import { useMutation } from "@tanstack/react-query";
import api from "api/axiosInstance";

interface ParseResponse {
  question_list: string[];
  answer_list: string[];
}

export const useParseSelfIntro = () => {
  return useMutation({
    mutationFn: async (text: string) => {
      const response = await api.post(
        "/api/parse/convert",
        text,
        {
          headers: {
            "Content-Type": "text/plain",
          },
        },
      );
      return response.data.data as ParseResponse;
    },
  });
};