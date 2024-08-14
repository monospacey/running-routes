export default async function downloader(radius, latitude, longitude) {
  const url = "https://overpass-api.de/api/interpreter";
  const query = `[out:json];

    (
    way(around:${radius}, ${latitude}, ${longitude})[highway~"primary|secondary|residential|tertiary|path|footway|cycleway|service"];
  ) -> .good;
    
  
    (
    way(around:${radius}, ${latitude}, ${longitude})[landuse~"retail|industrial"];
    way(around:${radius}, ${latitude}, ${longitude})[amenity="school"];
  );
  
  
  
  map_to_area -> .a;
    
  way(area.a) -> .bad;
  
  way(around:${radius}, ${latitude}, ${longitude})[service~"driveway|parking_aisle"] -> .c;
  
  (way.good; - way.bad;); (._; - way.c; );
  
  
  out geom meta;`;
  let result = await fetch(url, {
    method: "POST",
    body: query,
  }).then((data) => data.json());
  return result;
}
