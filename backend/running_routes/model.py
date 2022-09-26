from abc import ABC, abstractmethod
import itertools
import math

import networkx as nx
from ortools.constraint_solver import routing_enums_pb2
from ortools.constraint_solver import pywrapcp
import osmnx
import shapely
from sklearn.cluster import KMeans

from running_routes.network import NetworkFactory

from typing import Dict, List, Tuple, Optional

CP_DEFAULT_PARAMETERS = {
    "sample_percent": 0.2,
    "max_sample_size": 100,
    "seed": 1234,
    "time_limit": 10
}


class ModelFactory(ABC):
    """Factory that represents different model implementations"""
    @abstractmethod
    def __init__(self, **kwargs):
        """Load parameters"""

    @abstractmethod
    def solve(self, n: int, distance: int, start_coordinate: Dict, network: NetworkFactory) -> List[List]:
        """Creates and solves the model"""


class CPModel(ModelFactory):
    """
    Implements a vehicle routing problem based model through
    constraint programming and OR-tools

    https://developers.google.com/optimization/routing/vrp
    https://developers.google.com/optimization/routing/penalties
    """

    def __init__(self, **parameters):
        self.parameters = parameters

        # Set default parameters
        for key, value in CP_DEFAULT_PARAMETERS.items():
            if key not in self.parameters:
                self.parameters[key] = value

    def solve(self, n: int, distance: int, start_coordinate: Dict, network: NetworkFactory) -> List[List]:
        sample_coordinates = self._downsample(
            network, self.parameters["sample_percent"], self.parameters["max_sample_size"], self.parameters["seed"])
        sample_nodes = self._find_sample_nodes(start_coordinate, sample_coordinates, network)
        distance_matrix = self._construct_distance_matrix(sample_nodes, network)
        manager, routing = self._construct_cp_model(n, distance, distance_matrix)
        assignment = self._solve_cp_model(
            routing, self.parameters["time_limit"])
        results = self._generate_results(
            n, sample_nodes, network,
            routing, manager,
            assignment)
        return results

    def _downsample(self, network: NetworkFactory, sample_percent: float, max_sample_size: int, seed: int) -> List[Dict]:
        """Downsample using KMeans"""
        coordinates = [
            [data["y"], data["x"]]
            for _, data in network.nodes.items()
        ]
        percent_sample_size = int(len(coordinates)*sample_percent)
        sample_size = percent_sample_size if percent_sample_size < max_sample_size else max_sample_size
        kmeans = KMeans(n_clusters=sample_size,
                        random_state=seed).fit(coordinates)
        sample_coordinates = [
            {"lat": center[0], "lng": center[1]}
            for center in kmeans.cluster_centers_
        ]
        return sample_coordinates

    def _find_sample_nodes(
            self, start_coordinate: Dict, sample_coordinates: List[Dict],
            network: NetworkFactory) -> List:
        # `location` is the zeroth element by construction
        # Remove any duplicate nodes
        # https://stackoverflow.com/a/17016257
        model_coordinates = [start_coordinate] + sample_coordinates
        nearest_nodes = network.nearest_nodes(model_coordinates)
        sample_nodes = list(dict.fromkeys(nearest_nodes))
        return sample_nodes

    def _construct_distance_matrix(self, sample_nodes: List, network: NetworkFactory) -> List[List[float]]:
        # If there are no path between source and target, return `self.total_length`
        distance_matrix = []
        for source in sample_nodes:
            distance_from_source = []
            for target in sample_nodes:
                try:
                    length = network.length(source, target)
                except nx.NodeNotFound:
                    length = self.distance
                distance_from_source.append(length)
            distance_matrix.append(distance_from_source)

        return distance_matrix

    def _construct_cp_model(
            self, n: int, distance: int,
            distance_matrix: List[List],
    ) -> Tuple[pywrapcp.RoutingIndexManager, pywrapcp.RoutingModel]:
        """
        Follows the vrp model with drop penalties
        https://developers.google.com/optimization/routing/vrp
        """
        if not distance_matrix:
            raise Exception("Invalid distance_matrix")

        # The depot is the zeroth element by construction
        manager = pywrapcp.RoutingIndexManager(
            len(distance_matrix), n, 0)
        routing = pywrapcp.RoutingModel(manager)

        def distance_callback(from_index, to_index):
            """
            Create and register transit callback
            Returns the distance between the two nodes
            """
            from_node = manager.IndexToNode(from_index)
            to_node = manager.IndexToNode(to_index)
            return distance_matrix[from_node][to_node]
        transit_callback_index = routing.RegisterTransitCallback(
            distance_callback)

        routing.SetArcCostEvaluatorOfAllVehicles(transit_callback_index)
        dimension_name = "distance"
        routing.AddDimension(
            transit_callback_index, 0, distance, True, dimension_name)

        # Add the ability to drop nodes for a penalty
        drop_penalty = n*distance
        for node in range(1, len(distance_matrix)):
            routing.AddDisjunction([manager.NodeToIndex(node)], drop_penalty)

        return manager, routing

    def _solve_cp_model(
            self, routing: pywrapcp.RoutingIndexManager, time_limit: float
    ) -> pywrapcp.Assignment:
        # Use the suggested search strategy
        search_parameters = pywrapcp.DefaultRoutingSearchParameters()
        search_parameters.first_solution_strategy = (
            routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC)
        search_parameters.local_search_metaheuristic = (
            routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH)
        search_parameters.time_limit.seconds = time_limit

        assignment = routing.SolveWithParameters(search_parameters)
        return assignment

    def _generate_results(
            self,
            n: int,
            candidate_nodes: List,
            network: NetworkFactory,
            routing: pywrapcp.RoutingIndexManager,
            manager: pywrapcp.RoutingModel,
            assignment: pywrapcp.Assignment) -> List[List]:
        """Returns the paths in the context of network nodes"""
        results = []

        for route_id in range(n):
            index = routing.Start(route_id)
            candidate_tour = []

            # Extract the tour from candidate nodes and cp model
            while not routing.IsEnd(index):
                node_index = manager.IndexToNode(index)
                candidate_tour.append(candidate_nodes[node_index])
                index = assignment.Value(routing.NextVar(index))
            node_index = manager.IndexToNode(index)
            candidate_tour.append(candidate_nodes[node_index])
            results.append(candidate_tour)

        return results


SAVINGS_DEFAULT_PARAMETERS = {
    "sample_percent": 0.2,
    "max_sample_size": 100,
    "seed": 1234,
    "max_node": 8
}


class SavingsModel(ModelFactory):
    """
    Implements a modified version of the Clarke Wright's savings algorithm
    https://web.mit.edu/urban_or_book/www/book/chapter6/6.4.12.html
    """

    def __init__(self, **parameters):
        self.parameters = parameters

        # Set default parameters
        for key, value in SAVINGS_DEFAULT_PARAMETERS.items():
            if key not in self.parameters:
                self.parameters[key] = value

    def solve(self, n: int, distance: int, start_coordinate: Dict, network: NetworkFactory) -> List[List]:
        sample_coordinates = self._downsample(
            network, self.parameters["sample_percent"], self.parameters["max_sample_size"], self.parameters["seed"])
        sample_nodes = self._find_sample_nodes(start_coordinate, sample_coordinates, network)
        savings = self._calculate_savings(sample_nodes, network)

        depot = sample_nodes[0]
        routes = [[depot, node, depot] for node in sample_nodes[1:]]

        for saving in savings:
            routes = self._merge_routes(saving, routes, network, self.parameters["max_node"], distance)

        results = self._circularity_filter(n, routes, network)
        return results

    def _downsample(self, network: NetworkFactory, sample_percent: float, max_sample_size: int, seed: int) -> List[Dict]:
        """Downsample using KMeans"""
        coordinates = [
            [data["y"], data["x"]]
            for _, data in network.nodes.items()
        ]
        percent_sample_size = int(len(coordinates)*sample_percent)
        sample_size = percent_sample_size if percent_sample_size < max_sample_size else max_sample_size
        kmeans = KMeans(n_clusters=sample_size, random_state=seed).fit(coordinates)
        sample_coordinates = [
            {"lat": center[0], "lng": center[1]}
            for center in kmeans.cluster_centers_
        ]
        return sample_coordinates

    def _find_sample_nodes(
            self, start_coordinate: Dict, sample_coordinates: List[Dict],
            network: NetworkFactory) -> List:
        # `location` is the zeroth element by construction
        # Remove any duplicate nodes
        # https://stackoverflow.com/a/17016257
        model_coordinates = [start_coordinate] + sample_coordinates
        nearest_nodes = network.nearest_nodes(model_coordinates)
        sample_nodes = list(dict.fromkeys(nearest_nodes))
        return sample_nodes

    def _calculate_savings(self, sample_nodes: List, network: NetworkFactory) -> Dict[Tuple, float]:
        # If there are no path between source and target, return `self.total_length`
        savings = {}

        depot = sample_nodes[0]
        for source, target in itertools.combinations(sample_nodes[1:], 2):
            savings[source, target] = network.length(
                depot, source) + network.length(target, depot) - network.length(source, target)

        # https://stackoverflow.com/a/613218
        sorted_savings = {edge: length for edge, length in sorted(savings.items(), key=lambda item: item[1])}
        return sorted_savings

    def _rotate_interior_route(self, route: List, source: int, target: Optional[int] = None) -> List:
        start_node, *interior_nodes, _ = route
        source_index = route.index(source)

        direction = 1
        if target:
            target_index = route.index(target)
            direction = source_index - target_index
            if abs(direction) != 1:
                raise Exception(f"{source} and {target} are not adjacent in {route}")

        return interior_nodes[source_index-1::direction] + interior_nodes[:source_index-1:direction]

    def _split_route(self, route: List, source: int, target: int) -> List:
        source_index = route.index(source)
        target_index = route.index(target)

        direction = target_index - source_index
        if abs(direction) != 1:
            raise Exception(f"{source} and {target} are not adjacent in {route}")
        elif direction == 1:
            return route[:target_index], route[target_index:]
        else:
            return route[source_index:][::-1], route[:source_index][::-1]

    def _merge_routes(self, saving: Tuple, routes: List[List], network: NetworkFactory, max_node: int, distance: int):
        start_node = routes[0][0]
        route_0 = next(route for route in routes if saving[0] in route)
        route_1 = next(route for route in routes if saving[1] in route)
        saving_0_index = route_0.index(saving[0])
        saving_1_index = route_1.index(saving[1])

        # If the routes are the same, do not merge
        if route_0 == route_1:
            return routes

        # If the number of nodes between the two routes exceed the limit, do not merge
        if len(route_0) + len(route_1) - 2 > max_node:
            return routes

        # saving contains two exterior node
        if saving_0_index in [1, len(route_0)-2] and saving_1_index in [1, len(route_1)-2]:
            outer_route = self._rotate_interior_route(route_0, saving[0])[::-1]
            inner_route = self._rotate_interior_route(route_1, saving[1])
            merged_route = [start_node] + outer_route + inner_route + [start_node]

        # Saving contains one exterior node
        elif saving_0_index in [1, len(route_0)-2] or saving_1_index in [1, len(route_1)-2]:
            if saving_1_index in [1, len(route_1)-2]:
                outer_route = route_0
                inner_route = self._rotate_interior_route(route_1, saving[1])
                outer_saving_index = saving_0_index
            else:
                outer_route = route_1
                inner_route = self._rotate_interior_route(route_0, saving[0])
                outer_saving_index = saving_1_index

            adjacent_outer_saving_nodes = [
                outer_route[outer_saving_index-1],
                outer_route[outer_saving_index+1]
            ]
            crossings = {
                outer: network.length(outer, inner_route[-1])
                for outer in adjacent_outer_saving_nodes
            }
            outer_crossing = min(crossings, key=crossings.get)

            first_split, second_split = self._split_route(
                outer_route, outer_route[outer_saving_index], outer_crossing)

            merged_route = first_split + inner_route + second_split

        # Saving contains no exterior node
        else:
            if ((
                network.length(start_node, route_0[1]) + network.length(route_0[-2],
                                                                        start_node) + network.length(route_1[1], route_1[-2])
            ) < (
                network.length(start_node, route_1[1]) + network.length(route_1[-2],
                                                                        start_node) + network.length(route_0[1], route_0[-2])
            )):
                outer_route, inner_route = route_0, route_1
                outer_saving_index, inner_saving_index = saving_0_index, saving_1_index
            else:
                outer_route, inner_route = route_1, route_0
                outer_saving_index, inner_saving_index = saving_1_index, saving_0_index

            adjacent_outer_saving_nodes = [
                outer_route[outer_saving_index-1],
                outer_route[outer_saving_index+1]
            ]
            adjacent_inner_saving_nodes = [
                inner_route[inner_saving_index-1],
                inner_route[inner_saving_index+1]
            ]
            crossings = {
                (outer, inner): network.length(outer, inner)
                for outer, inner in itertools.product(adjacent_outer_saving_nodes, adjacent_inner_saving_nodes)
            }
            outer_crossing, inner_crossing = min(crossings, key=crossings.get)
            first_split, second_split = self._split_route(
                outer_route, outer_route[outer_saving_index], outer_crossing)
            rotated_inner_route = self._rotate_interior_route(
                inner_route, inner_route[inner_saving_index], inner_crossing)
            merged_route = first_split + rotated_inner_route + second_split

        if sum(network.length(source, target) for source, target in zip(merged_route, merged_route[1:])) > distance:
            return routes

        return [route for route in routes if route not in [route_0, route_1]] + [merged_route]

    def _circularity_filter(self, n: int, routes: List[List], network: NetworkFactory) -> List[List]:
         # https://sciencing.com/calculate-circularity-5138742.html
        measurement = {}
        for i, route in enumerate(routes):
            extended_route = []
            for source, target in zip(route, route[1:]):
                extended_route.extend(network.path(source, target))
            extended_route += [extended_route[0]]
            extended_route = [group[0] for group in itertools.groupby(extended_route)]

            subgraph = network.graph.subgraph(extended_route)
            projected_subgraph = osmnx.projection.project_graph(subgraph)
            y_coordinates = nx.get_node_attributes(projected_subgraph, "y")
            x_coordinates = nx.get_node_attributes(projected_subgraph, "x")

            routes_to_xy = [
                [x_coordinates[node], y_coordinates[node]]
                for node in extended_route]
            polygon = shapely.geometry.Polygon(routes_to_xy)
            area = polygon.area
            perimeter = polygon.length
            measurement[i] = 4*math.pi * area / perimeter**2
        sorted_data = [i for i, _ in sorted(measurement.items(), key=lambda item: item[1], reverse=True)]

        results = [routes[i] for i in sorted_data[:n]]
        return results


class GreedySavingsModel(ModelFactory):
    """
    Implements a modified version of the Clarke Wright's savings algorithm
    https://web.mit.edu/urban_or_book/www/book/chapter6/6.4.12.html
    """

    def __init__(self, **parameters):
        self.parameters = parameters

        # Set default parameters
        for key, value in SAVINGS_DEFAULT_PARAMETERS.items():
            if key not in self.parameters:
                self.parameters[key] = value

    def solve(self, n: int, distance: int, start_coordinate: Dict, network: NetworkFactory) -> List[List]:
        sample_coordinates = self._downsample(
            network, self.parameters["sample_percent"], self.parameters["max_sample_size"], self.parameters["seed"])
        sample_nodes = self._find_sample_nodes(start_coordinate, sample_coordinates, network)
        savings = self._calculate_savings(sample_nodes, network)

        depot = sample_nodes[0]
        

        for saving in savings:
            routes = self._merge_routes(saving, routes, network, self.parameters["max_node"], distance)

        results = self._circularity_filter(n, routes, network)
        return results

    def _downsample(self, network: NetworkFactory, sample_percent: float, max_sample_size: int, seed: int) -> List[Dict]:
        """Downsample using KMeans"""
        coordinates = [
            [data["y"], data["x"]]
            for _, data in network.nodes.items()
        ]
        percent_sample_size = int(len(coordinates)*sample_percent)
        sample_size = percent_sample_size if percent_sample_size < max_sample_size else max_sample_size
        kmeans = KMeans(n_clusters=sample_size, random_state=seed).fit(coordinates)
        sample_coordinates = [
            {"lat": center[0], "lng": center[1]}
            for center in kmeans.cluster_centers_
        ]
        return sample_coordinates

    def _find_sample_nodes(
            self, start_coordinate: Dict, sample_coordinates: List[Dict],
            network: NetworkFactory) -> List:
        # `location` is the zeroth element by construction
        # Remove any duplicate nodes
        # https://stackoverflow.com/a/17016257
        model_coordinates = [start_coordinate] + sample_coordinates
        nearest_nodes = network.nearest_nodes(model_coordinates)
        sample_nodes = list(dict.fromkeys(nearest_nodes))
        return sample_nodes

    def _calculate_savings(self, sample_nodes: List, network: NetworkFactory) -> Dict[Tuple, float]:
        # If there are no path between source and target, return `self.total_length`
        savings = {}

        depot = sample_nodes[0]
        for source, target in itertools.combinations(sample_nodes[1:], 2):
            savings[source, target] = network.length(
                depot, source) + network.length(target, depot) - network.length(source, target)

        # https://stackoverflow.com/a/613218
        sorted_savings = {edge: length for edge, length in sorted(savings.items(), key=lambda item: item[1])}
        return sorted_savings

    def _find_best_edge(self, distance: int, tour: List, valid_nodes: List, savings: Dict, max_node: int, network: NetworkFactory)-> List:
        current_distance = sum(network.length(x, y) for x, y in zip(tour, tour[1:]))


    def _circularity_filter(self, n: int, routes: List[List], network: NetworkFactory) -> List[List]:
         # https://sciencing.com/calculate-circularity-5138742.html
        measurement = {}
        for i, route in enumerate(routes):
            extended_route = []
            for source, target in zip(route, route[1:]):
                extended_route.extend(network.path(source, target))
            extended_route += [extended_route[0]]
            extended_route = [group[0] for group in itertools.groupby(extended_route)]

            subgraph = network.graph.subgraph(extended_route)
            projected_subgraph = osmnx.projection.project_graph(subgraph)
            y_coordinates = nx.get_node_attributes(projected_subgraph, "y")
            x_coordinates = nx.get_node_attributes(projected_subgraph, "x")

            routes_to_xy = [
                [x_coordinates[node], y_coordinates[node]]
                for node in extended_route]
            polygon = shapely.geometry.Polygon(routes_to_xy)
            area = polygon.area
            perimeter = polygon.length
            measurement[i] = 4*math.pi * area / perimeter**2
        sorted_data = [i for i, _ in sorted(measurement.items(), key=lambda item: item[1], reverse=True)]

        results = [routes[i] for i in sorted_data[:n]]
        return results