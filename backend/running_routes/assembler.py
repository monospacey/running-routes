from abc import ABC, abstractmethod

from running_routes.network import NetworkFactory

from typing import List, Optional


class AssemblerFactory(ABC):
    @abstractmethod
    def __init__(self, **parameters):
        pass

    @abstractmethod
    def generate_output(
            self, tours: List[List], distance: int, network: NetworkFactory) -> List:
        pass


class TourAssembler(AssemblerFactory):
    """Converts nodes to coordiantes"""

    def __init__(self):
        pass

    def generate_output(self, tours: List[List], distance: int, network: NetworkFactory) -> List:
        network_nodes = network.nodes
        routes = [
            [[network_nodes[node]["y"], network_nodes[node]["x"]] for node in tour]
            for tour in tours]
        return routes


class RestAPIAssembler(AssemblerFactory):
    """Converts tours to routes with distance as metadata"""

    def __init__(self):
        pass

    def generate_output(self, tours: List[List], distance: int, network: NetworkFactory) -> List:
        network_nodes = network.nodes
        routes = {"routes": []}
        for tour in tours:
            coordinates = [[network_nodes[node]["y"], network_nodes[node]["x"]] for node in tour]
            route_distance = sum(network.length(x, y) for x, y in zip(tour, tour[1:]))
            url = (
                "https://google.com/maps/dir/"
                + "/".join([f"""{network_nodes[node]["y"]},{network_nodes[node]["x"]}""" for node in tour])
                + "/data=!3m1!4b1!4m2!4m1!3e2" # Mode of transport set to walking
            )
            route = {"coordinates": coordinates, "distance": route_distance, "url": url}
            routes["routes"].append(route)
        return routes
