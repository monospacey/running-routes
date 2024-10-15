import Genetic from "genetic-js";
// import * as hull from "@thi.ng/geom-hull";
// import { convexHull } from "@thi.ng/geom";

let genetic = Genetic.create();

genetic.optimize = Genetic.Optimize.Minimize;
genetic.select1 = Genetic.Select1.Tournament2;
genetic.select2 = Genetic.Select2.Tournament2;
genetic.lastSolution = null;

genetic.repairHeuristic = function (entity) {
  // Must have at least 2 values as 1
  const minimumNodes = 3;
  const numberOfOnes = entity.reduce(
    (accumulator, currentValue) => accumulator + currentValue,
    0
  );
  const difference1 = minimumNodes - numberOfOnes;
  if (difference1 <= 0) {
    return entity;
  } else {
    let indexOfZeros = []
    entity.map((x, i) => {
      if (x == 0) {
        indexOfZeros.push(i)
      }
    });

    let shuffledIndicies = indexOfZeros
      .map((value) => ({ value, sort: Math.random() }))
      .sort((a, b) => a.sort - b.sort)
      .map(({ value }) => value)
      .slice(0, difference1);

    return entity.map((x, i) => (shuffledIndicies.includes(i) ? 1 : x));
  }
};

genetic.medoidNames = function () {
  return Object.keys(genetic.userData.medoidNodes);
};
genetic.optionalMemoids = function () {
  return genetic
    .medoidNames()
    .filter((mn) => mn != genetic.userData.rootMedoid);
};
genetic.grahamScan2 = function (pts, eps = 1e-6) {
  const num = pts.length;
  if (num <= 3) return pts.slice();
  let h = 1;
  let i;
  let p;
  let q;
  let r;
  let rx;
  let ry;
  const min = genetic.__findMin(pts);
  [rx, ry] = pts[min];
  const sorted = [];
  for (i = 0; i < num; i++) {
    p = pts[i];
    sorted[i] = { p, t: Math.atan2(p[1] - ry, p[0] - rx) };
  }
  sorted.sort((a, b) => (a.t !== b.t ? a.t - b.t : a.p[0] - b.p[0]));
  const hull = [sorted[0].p];
  for (i = 1; i < num; i++) {
    p = hull[h - 2];
    q = hull[h - 1];
    r = sorted[i].p;
    rx = r[0];
    ry = r[1];
    while (
      (h > 1 && genetic.__notCCW(p[0], p[1], q[0], q[1], rx, ry, eps)) ||
      (h === 1 && q[0] === rx && q[1] === ry)
    ) {
      h--;
      q = p;
      p = hull[h - 2];
    }
    hull[h++] = r;
  }
  hull.length = h;
  return hull;
};
genetic.__notCCW = function (ax, ay, bx, by, cx, cy, eps) {
  (by - ay) * (cx - ax) >= (bx - ax) * (cy - ay) - eps;
};
genetic.__findMin = function (pts) {
  let n = pts.length - 1;
  let minID = n;
  let [minX, minY] = pts[n];
  let p, y;
  for (; n-- > 0; ) {
    p = pts[n];
    y = p[1];
    if (y < minY || (y === minY && p[0] < minX)) {
      minX = p[0];
      minY = y;
      minID = n;
    }
  }
  return minID;
};

// genetic.grahamScan2 = async function (x) {
//   const hull = await import("@thi.ng/geom-hull");
//   return hull.grahamScan2(x);
// };

genetic.seed = function () {
  // Generate a binary array whether a memoid is in the solution or not
  //  e.g. The first memoid is the only one part of the route -> [1, 0, 0,]
  let entity = Array.from({ length: genetic.optionalMemoids().length }).map(
    () => Math.round(Math.random())
  );
  return genetic.repairHeuristic(entity);
};

genetic.mutate = function (entity) {
  // Change the status of one memoid at random
  const randomIndex = Math.floor(
    Math.random() * genetic.optionalMemoids().length
  );
  let mutatedEntity = entity.map((x, i) => (i == randomIndex ? 1 - x : x));
  return genetic.repairHeuristic(mutatedEntity);
};

genetic.crossover = function (mother, father) {
  // Son is bitwise XOR operator on each element
  let son = mother.map((x, i) => x ^ father[i]);

  // Daughter is bitwise OR operator on each element
  let daughter = mother.map((x, i) => x | father[i]);

  let mutatedSon = genetic.repairHeuristic(son);
  let mutatedDaughter = genetic.repairHeuristic(daughter);
  return [mutatedSon, mutatedDaughter];
};

genetic.entityToMedoids = function (entity) {
  let optionalMedoidsCopy = [...genetic.optionalMemoids()];
  return optionalMedoidsCopy.filter((x, i) => entity[i] == 1);
};

genetic.findTripleNodeDistance = function (x, y, z) {
  return (
    genetic.userData.medoidEdges[`${x}-${y}`].distance +
    genetic.userData.medoidEdges[`${y}-${z}`].distance
  );
};

genetic.findRouteDistance = function (route) {
  let distance = 0;
  for (let i = -1; i < route.length - 1; i++) {
    distance +=
      genetic.userData.medoidEdges[`${route.at(i)}-${route.at(i + 1)}`].distance;
  }
  return distance;
};

genetic.presentRoute = function (route) {
  // Rotate the route so the rootMedoid is at the start and end
  const rootMedoidIndex = route.indexOf(genetic.userData.rootMedoid);
  let startRoute = route.slice(rootMedoidIndex);
  let middleRoute = route.slice(0, rootMedoidIndex);
  let endRoute = [genetic.userData.rootMedoid];
  return startRoute.concat(middleRoute).concat(endRoute);
};

genetic.findRoute = function (entity) {
  let medoidNodes = genetic.userData.medoidNodes;
  let medoids = [genetic.userData.rootMedoid].concat(
    genetic.entityToMedoids(entity)
  );
  let positions = medoids.map((m) => [medoidNodes[m].x, medoidNodes[m].y]);
  let originalHull = genetic.grahamScan2(positions);
  let route = originalHull.map((e) => {
    let index = positions.indexOf(e);
    return medoids[index];
  });

  let unallocatedMedoids = medoids.filter((e) => !route.includes(e));
  const numberToAllocate = unallocatedMedoids.length;
  for (
    let allocationCount = 0;
    allocationCount <= numberToAllocate - 1;
    allocationCount++
  ) {
    let candidateTriplets = [];
    unallocatedMedoids.map((y) => {
      for (let i = -1; i < route.length - 1; i++) {
        let x = route.at(i);
        let z = route.at(i + 1);
        candidateTriplets.push({
          x: x,
          y: y,
          z: z,
          distance: genetic.findTripleNodeDistance(x, y, z),
        });
      }
    });
    let shortestTriplet = candidateTriplets.reduce((prev, curr) =>
      prev.distance < curr.distance ? prev : curr
    );
    let insertionIndex = route.indexOf(shortestTriplet.x);
    route.splice(insertionIndex, 0, shortestTriplet.y);
    unallocatedMedoids.splice(unallocatedMedoids.indexOf(shortestTriplet.y), 1);
  }
  return route;
};
genetic.fitness = function (entity) {
  let route = genetic.findRoute(entity);
  let distance = genetic.findRouteDistance(route);
  return Math.abs(distance - genetic.userData.distance);
};

genetic.generation = function(population, generation, stats) {
  // Add the ability to stop the genetic algorithm when it is near enough
  // Currently set to 0.5% of the target distance
  const threshold = 0.005
  let entity = population[0].entity;
  if (genetic.fitness(entity) <= threshold*genetic.userData.distance){
    return false
  } 
}

genetic.notification = function (population, generation, stats, isFinished) {
  let entity = population[0].entity;
  let route = genetic.findRoute(entity);
  let routeDistance = genetic.findRouteDistance(route);
  genetic.lastSolution = {
    routeDistance: routeDistance,
    route: route,
    niceRoute: genetic.presentRoute(route),
    rootMedoid: genetic.userData.rootMedoid,
  };
};

export default genetic;
