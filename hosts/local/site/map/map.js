require([
  "esri/Map",
  "esri/views/MapView",
  "esri/layers/GeoJSONLayer",
  "esri/layers/GraphicsLayer",
  "esri/Graphic"
], (Map, MapView, GeoJSONLayer, GraphicsLayer, Graphic) => {
  const colors = {
    "5": [253, 208, 162, 0.72],
    "6": [253, 141, 60, 0.76],
    "7": [227, 74, 51, 0.8],
    "8+": [139, 0, 0, 0.84]
  };
  const map = new Map({ basemap: null });
  const view = new MapView({
    container: "view",
    map,
    center: [172.5, -41.2],
    zoom: 5,
    constraints: { minZoom: 4, maxZoom: 11 }
  });
  const outline = new GeoJSONLayer({
    url: "data/nz-outline.geojson",
    renderer: {
      type: "simple",
      symbol: {
        type: "simple-fill",
        color: [235, 239, 241, 1],
        outline: { color: [75, 89, 99, 1], width: 0.7 }
      }
    }
  });
  const eventLayer = new GraphicsLayer();
  map.addMany([outline, eventLayer]);
  let exposureLayer;

  function renderer() {
    return {
      type: "unique-value",
      field: "mmi_band",
      uniqueValueInfos: Object.entries(colors).map(([value, color]) => ({
        value,
        symbol: {
          type: "simple-fill",
          color,
          outline: { color: [92, 92, 92, 0.45], width: 0.25 }
        }
      }))
    };
  }

  function showEvent(event) {
    if (exposureLayer) map.remove(exposureLayer);
    exposureLayer = new GeoJSONLayer({
      url: event.data_file,
      renderer: renderer(),
      popupTemplate: {
        title: "MMI {mmi}",
        content: [
          { type: "fields", fieldInfos: [
            { fieldName: "event_building_count", label: "Buildings at event" },
            { fieldName: "current_building_count", label: "Current buildings" },
            { fieldName: "population_2023", label: "Population 2023", format: { digitSeparator: true, places: 0 } },
            { fieldName: "mmi_source", label: "MMI source" },
            { fieldName: "source_version", label: "Source version" }
          ] }
        ]
      }
    });
    map.add(exposureLayer, 1);
    eventLayer.removeAll();
    eventLayer.add(new Graphic({
      geometry: { type: "point", longitude: event.longitude, latitude: event.latitude },
      symbol: { type: "simple-marker", color: "#111827", size: 9, outline: { color: "white", width: 1 } },
      popupTemplate: { title: event.event_name, content: `M${event.magnitude}, depth ${event.depth_km} km` }
    }));
    document.getElementById("event-summary").textContent =
      `M${event.magnitude} | max populated MMI ${event.max_mmi ?? "n/a"}`;
  }

  fetch("data/events.json")
    .then((response) => response.json())
    .then((events) => {
      const select = document.getElementById("event-select");
      events.forEach((event, index) => {
        const option = document.createElement("option");
        option.value = String(index);
        option.textContent = `${event.event_name} (M${event.magnitude})`;
        select.append(option);
      });
      select.addEventListener("change", () => showEvent(events[Number(select.value)]));
      if (events.length) showEvent(events[0]);
    });
});
