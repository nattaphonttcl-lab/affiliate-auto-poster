import http from "k6/http";
import { check } from "k6";

export const options = {
  stages: [
    { duration: "30s", target: 50 },
    { duration: "60s", target: 100 },
    { duration: "30s", target: 0 },
  ],
  thresholds: {
    http_req_duration: ["p(99)<1000"],
  },
};

export default function () {
  const res = http.get("http://localhost:8000/api/v1/health/readiness");
  check(res, {
    "status 200": (r) => r.status === 200,
  });
}
