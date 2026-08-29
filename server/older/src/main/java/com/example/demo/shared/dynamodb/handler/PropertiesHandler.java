package com.example.demo.shared.dynamodb.handler;

import com.example.demo.config.DynamoDBProperties;
import com.example.demo.shared.properties.domain.Properties;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Component;
import software.amazon.awssdk.services.dynamodb.DynamoDbClient;
import software.amazon.awssdk.services.dynamodb.model.AttributeValue;
import software.amazon.awssdk.services.dynamodb.model.GetItemRequest;
import software.amazon.awssdk.services.dynamodb.model.GetItemResponse;
import software.amazon.awssdk.services.dynamodb.model.PutItemRequest;

import java.util.HashMap;
import java.util.Map;
import java.util.Optional;

/**
 * Properties 관련 DynamoDB 작업을 처리하는 핸들러
 * 시스템 설정 CRUD 기능을 제공합니다.
 */
@Component
@RequiredArgsConstructor
@Slf4j
public class PropertiesHandler {

    private final DynamoDbClient dynamoDbClient;
    private final DynamoDBProperties dynamoDBProperties;

    /**
     * 시스템 설정 저장
     * @param properties 시스템 설정
     * @return 저장된 시스템 설정
     */
    public Properties saveProperties(Properties properties) {
        Map<String, AttributeValue> item = new HashMap<>();
        item.put("id", AttributeValue.builder().s("properties").build());
        
        if (properties.getMaxAccessCodePerDay() != null) {
            item.put("maxAccessCodePerDay", AttributeValue.builder().n(String.valueOf(properties.getMaxAccessCodePerDay())).build());
        }
        if (properties.getMaxAnalysisPerDay() != null) {
            item.put("maxAnalysisPerDay", AttributeValue.builder().n(String.valueOf(properties.getMaxAnalysisPerDay())).build());
        }

        PutItemRequest putItemRequest = PutItemRequest.builder()
                .tableName(dynamoDBProperties.getTables().getProperties())
                .item(item)
                .build();

        try {
            dynamoDbClient.putItem(putItemRequest);
            return properties;
        } catch (Exception e) {
            log.error("Error saving properties", e);
            throw new RuntimeException("Failed to save properties", e);
        }
    }

    /**
     * 시스템 설정 조회
     * @return 시스템 설정
     */
    public Optional<Properties> findProperties() {
        Map<String, AttributeValue> key = new HashMap<>();
        key.put("id", AttributeValue.builder().s("properties").build());

        GetItemRequest getItemRequest = GetItemRequest.builder()
                .tableName(dynamoDBProperties.getTables().getProperties())
                .key(key)
                .build();

        try {
            GetItemResponse response = dynamoDbClient.getItem(getItemRequest);
            
            if (!response.hasItem()) {
                return Optional.empty();
            }

            return Optional.of(mapToProperties(response.item()));
        } catch (Exception e) {
            log.error("Error finding properties", e);
            return Optional.empty();
        }
    }

    private Properties mapToProperties(Map<String, AttributeValue> item) {
        Properties properties = new Properties();
        
        if (item.containsKey("maxAccessCodePerDay")) {
            try {
                properties.setMaxAccessCodePerDay(Integer.parseInt(item.get("maxAccessCodePerDay").n()));
            } catch (Exception e) {
                log.warn("Failed to parse maxAccessCodePerDay");
            }
        }
        if (item.containsKey("maxAnalysisPerDay")) {
            try {
                properties.setMaxAnalysisPerDay(Integer.parseInt(item.get("maxAnalysisPerDay").n()));
            } catch (Exception e) {
                log.warn("Failed to parse maxAnalysisPerDay");
            }
        }
        
        return properties;
    }
}

