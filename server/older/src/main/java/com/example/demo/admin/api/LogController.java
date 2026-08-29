package com.example.demo.admin.api;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import lombok.Data;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.stereotype.Controller;
import org.springframework.ui.Model;
import org.springframework.web.bind.annotation.CookieValue;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RestController;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.regex.Matcher;
import java.util.regex.Pattern;
import java.util.stream.Collectors;
import java.util.stream.Stream;

@Controller
@RequiredArgsConstructor
public class LogController {


    @GetMapping("/admin/logs/{date}")
    public String getLogByDate(@PathVariable String date, Model model) throws IOException {
        Path logPath = Paths.get("logs/info." + date + ".log");
        if (!Files.exists(logPath)) {
            model.addAttribute("error", "해당 날짜의 로그가 없습니다.");
            return "logs";
        }

        Pattern pattern = Pattern.compile(
                "(\\d{4}-\\d{2}-\\d{2} \\d{2}:\\d{2}:\\d{2}) \\[(.*?)] INFO\\s+(.*?) - (\\{.*})"
        );
        ObjectMapper mapper = new ObjectMapper();

        List<InfoLogEntry> logs = Files.lines(logPath)
                .map(pattern::matcher)
                .filter(Matcher::matches)
                .map(m -> {
                    InfoLogEntry entry = new InfoLogEntry();
                    entry.setTimestamp(LocalDateTime.parse(
                            m.group(1),
                            DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss")
                    ));
                    entry.setThread(m.group(2));
                    entry.setLogger(m.group(3));

                    try {
                        Map<String, Object> jsonMap = mapper.readValue(m.group(4), new TypeReference<>() {});
                        entry.setCode(jsonMap.getOrDefault("code", "").toString());
                        entry.setEmail(jsonMap.getOrDefault("email", "").toString());
                        entry.setAccessCode(jsonMap.getOrDefault("accessCode", "").toString());
                        entry.setRequired(jsonMap.getOrDefault("required", "").toString());
                        entry.setMsg(jsonMap.getOrDefault("msg", "").toString());
                    } catch (Exception e) {
                        entry.setMsg(m.group(4));
                    }

                    return entry;
                })
                .toList();

        // 코드별 카운트
        Map<String, Long> codeCounts = logs.stream()
                .collect(Collectors.groupingBy(InfoLogEntry::getCode, Collectors.counting()));

        model.addAttribute("date", date);
        model.addAttribute("logs", logs);
        model.addAttribute("codeCounts", codeCounts);

        return "logs";
    }

    @Data
    public static class InfoLogEntry {
        private LocalDateTime timestamp;
        private String thread;
        private String logger;
        private String code = "";        // default 빈값
        private String email = "";
        private String accessCode = "";
        private String required = "";
        private String msg = "";
    }
}

