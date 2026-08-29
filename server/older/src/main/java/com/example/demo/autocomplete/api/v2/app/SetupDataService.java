package com.example.demo.autocomplete.api.v2.app;

import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import jakarta.annotation.PostConstruct;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.core.io.Resource;
import org.springframework.core.io.ResourceLoader;
import org.springframework.stereotype.Service;

import java.io.IOException;
import java.io.InputStream;
import java.util.Collections;
import java.util.List;

@Slf4j
@Service
@RequiredArgsConstructor
public class SetupDataService {

    private static final String SETUP_PREFIX = "classpath:setup/";

    private final ObjectMapper objectMapper;
    private final ResourceLoader resourceLoader;

    private List<String> companies = List.of();
    private List<String> positions = List.of();
    private List<String> universities = List.of();
    private List<String> majors = List.of();

    @PostConstruct
    void load() {
        companies = readStrings("companies.json");
        positions = readStrings("positions.json");
        universities = readStrings("universities.json");
        majors = readStrings("majors.json");
    }

    public List<String> companies() {
        return companies;
    }

    public List<String> positions() {
        return positions;
    }

    public List<String> universities() {
        return universities;
    }

    public List<String> majors() {
        return majors;
    }

    private List<String> readStrings(String fileName) {
        Resource resource = resourceLoader.getResource(SETUP_PREFIX + fileName);
        if (!resource.exists()) {
            return List.of();
        }
        try (InputStream in = resource.getInputStream()) {
            List<String> parsed = objectMapper.readValue(in, new TypeReference<List<String>>() {
            });
            return parsed != null ? List.copyOf(parsed) : List.of();
        } catch (IOException e) {
            log.warn("Failed to load setup list: {}", fileName, e);
            return Collections.emptyList();
        }
    }
}
