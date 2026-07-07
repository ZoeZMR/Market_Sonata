// react-plotly.js by default pulls the full plotly.js source. We bind it to
// the smaller pre-built `plotly.js-dist-min` bundle instead, via the factory.
// @ts-expect-error - dist-min ships without bundled types
import Plotly from "plotly.js-dist-min";
import createPlotlyComponent from "react-plotly.js/factory";

const Plot = createPlotlyComponent(Plotly);
export default Plot;
