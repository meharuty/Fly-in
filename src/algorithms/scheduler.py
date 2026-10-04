from src.simulation.movement import Movement
from src.models.drone import Drone
from src.models.zone import Zone, ZoneType
from src.models.connection import Connection


class Scheduler:
    def __init__(
        self,
        paths: list[list[Zone]],
        nb_drones: int,
        connections: list[Connection],
    ):
        self.paths = paths
        self.nb_drones = nb_drones
        self.connections = connections

    def create_drones(self) -> list[Drone]:
        drones = []

        for i in range(self.nb_drones):
            path = self.paths[i % len(self.paths)]

            drone = Drone(
                id=i + 1,
                curr_location=path[0],
                path=path.copy(),
            )

            drones.append(drone)

        return drones

    def get_next_zone(self, drone: Drone) -> Zone | None:
        current_index = drone.path.index(drone.curr_location)

        if current_index >= len(drone.path) - 1:
            return None

        return drone.path[current_index + 1]

    def propose_move(self, drone: Drone) -> Movement | None:
        next_zone = self.get_next_zone(drone)

        if next_zone is None:
            return None

        return Movement(
            drone_id=drone.id,
            current=drone.curr_location,
            destination=next_zone,
        )

    def simulate_turn(self, state):
        proposed_moves = []
        completed_moves = []
        just_arrived = set()

        for drone in state.drones:
            if drone.remaining_turns > 0:
                drone.remaining_turns -= 1

                if drone.remaining_turns == 0:
                    current_index = drone.path.index(
                        drone.curr_location
                    )
                    destination = drone.path[current_index + 1]

                    completed_moves.append(
                        Movement(
                            drone_id=drone.id,
                            current=drone.curr_location,
                            destination=destination,
                        )
                    )

                    drone.curr_location = destination
                    drone.active_connection = None
                    just_arrived.add(drone.id)

        for drone in state.drones:
            if drone.remaining_turns > 0:
                continue

            if drone.id in just_arrived:
                continue

            move = self.propose_move(drone)

            if move is not None:
                proposed_moves.append(move)

        valid_moves = self.resolve_conflicts(
            proposed_moves,
            state,
        )

        for move in valid_moves:
            drone = next(
                d for d in state.drones
                if d.id == move.drone_id
            )

            if move.destination.zone_type == ZoneType.RESTRICTED:
                drone.remaining_turns = 1
                drone.active_connection = frozenset(
                    (
                        move.current.name,
                        move.destination.name,
                    )
                )
            else:
                drone.curr_location = move.destination

        return valid_moves + completed_moves

    def resolve_conflicts(
        self,
        moves: list[Movement],
        state,
    ) -> list[Movement]:
        valid_moves = []
        occupancy: dict[str, int] = {}

        for drone in state.drones:
            zone_name = drone.curr_location.name
            occupancy[zone_name] = (
                occupancy.get(zone_name, 0) + 1
            )

        for move in moves:
            occupancy.setdefault(
                move.destination.name,
                0,
            )

        occupied_connections: dict[frozenset[str], int] = {}

        for drone in state.drones:
            if drone.active_connection is not None:
                key = drone.active_connection

                occupied_connections[key] = (
                    occupied_connections.get(key, 0) + 1
                )

        used_connections: dict[frozenset[str], int] = {}

        for move in moves:
            current = move.current
            destination = move.destination

            connection_key = frozenset(
                (
                    current.name,
                    destination.name,
                )
            )

            connection = None

            for conn in self.connections:
                if frozenset(
                    (
                        conn.zone_a.name,
                        conn.zone_b.name,
                    )
                ) == connection_key:
                    connection = conn
                    break

            if connection is None:
                continue

            occupied = occupied_connections.get(
                connection_key,
                0,
            )

            used = used_connections.get(
                connection_key,
                0,
            )

            if (
                occupied + used
                >= connection.max_link_capacity
            ):
                continue

            occupancy[current.name] -= 1

            is_start_or_end = (
                destination == state.start
                or destination == state.end
            )

            if (
                not is_start_or_end
                and occupancy[destination.name]
                >= destination.max_drones
            ):
                occupancy[current.name] += 1
                continue

            occupancy[destination.name] += 1

            used_connections[connection_key] = (
                used + 1
            )
            valid_moves.append(move)

        return valid_moves
