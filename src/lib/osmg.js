export default async function downloader(radius, latitude, longitude) {
  const url = "https://overpass-api.de/api/interpreter";
  const query = `[out:json];

    (
    way(around:${radius}, ${latitude}, ${longitude})[highway~"primary|secondary|tertiary|residential|path|cycleway|pedestrian"];
  ) -> .good;
    
  
    (
    way(around:${radius}, ${latitude}, ${longitude})[landuse~"retail"];
    way(around:${radius}, ${latitude}, ${longitude})[amenity="school"];
    way(around:${radius}, ${latitude}, ${longitude})[builing="yes"];
  );
  
  
  
  map_to_area -> .a;
    
  way(area.a) -> .bad;
  
  way(around:${radius}, ${latitude}, ${longitude})[service~"driveway|parking_aisle"] -> .c;
  way(around:${radius}, ${latitude}, ${longitude})[access~"private"] -> .d;
  
  (way.good; - way.bad;); (._; - way.c; );(._; - way.d; );

  
  
  out geom meta;`;
  let result = await fetch(url, {
    method: "POST",
    body: query,
  }).then((data) => data.json());
  return result;
}
