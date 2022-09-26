import pytest

from running_routes.assembler import RestAPIAssembler, TourAssembler
from running_routes.network import OSMNetwork


@pytest.fixture
def tours():
    return [[2384426953, 6806666960, 6806666961,  6806666960, 2384426953]]


@pytest.fixture
def distance():
    return 100


@pytest.fixture
def start_coordinate():
    return {"lat": -37.8102361, "lng": 144.9627652}


@pytest.fixture
def network(start_coordinate, distance):
    network = OSMNetwork()
    network.create(start_coordinate, distance)
    return network


@pytest.fixture
def tour_assembler():
    return TourAssembler()


@pytest.fixture
def rest_api_assembler():
    return RestAPIAssembler()


class TestTourAssembler:
    def test_generate_output(self, tours, distance, network, tour_assembler):
        route = [
            [-37.810335, 144.9632837], 
            [-37.8104393, 144.9629538], 
            [-37.8100645, 144.9626779], 
            [-37.8104393, 144.9629538], 
            [-37.810335, 144.9632837], 
        ]
        routes = tour_assembler.generate_output(tours, distance, network)
        assert routes[0] == route

class TestRestAPIAssembler:
    def test_generate_output(self, tours, distance, network, rest_api_assembler):
        coordinates = [
            [-37.810335, 144.9632837], 
            [-37.8104393, 144.9629538], 
            [-37.8100645, 144.9626779], 
            [-37.8104393, 144.9629538], 
            [-37.810335, 144.9632837], 
        ]
        routes = rest_api_assembler.generate_output(tours, distance, network)
        assert type(routes["routes"][0]["coordinates"]) == list
        assert int(routes["routes"][0]["distance"]) == 175