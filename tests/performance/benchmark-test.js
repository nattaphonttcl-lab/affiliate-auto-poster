import http from "k6/http";
import { Trend } from "k6/metrics";

const latency = new Trend("benchmark_latency");

export const options = {
  vus: 5,
  iterations: 200,
};

export default function () {
  const res = http.get("http://localhost:8000/api/v1/health");
  latency.add(res.timings.duration);
}
