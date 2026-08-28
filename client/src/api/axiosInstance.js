import axios from "axios";
import { API_BASE_URL } from "api/baseUrl";

const api = axios.create({
  baseURL: API_BASE_URL,
  withCredentials: true,
  headers: {
    "X-API-Version": "2",
  },
});

export default api;
