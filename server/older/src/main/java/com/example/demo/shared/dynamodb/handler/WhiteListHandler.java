package com.example.demo.shared.dynamodb.handler;

import com.example.demo.config.DynamoDBProperties;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Component;
import software.amazon.awssdk.services.dynamodb.DynamoDbClient;
import software.amazon.awssdk.services.dynamodb.model.AttributeValue;
import software.amazon.awssdk.services.dynamodb.model.DeleteItemRequest;
import software.amazon.awssdk.services.dynamodb.model.GetItemRequest;
import software.amazon.awssdk.services.dynamodb.model.GetItemResponse;
import software.amazon.awssdk.services.dynamodb.model.PutItemRequest;
import software.amazon.awssdk.services.dynamodb.model.ScanRequest;
import software.amazon.awssdk.services.dynamodb.model.ScanResponse;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

/**
 * WhiteList 관련 DynamoDB 작업을 처리하는 핸들러
 * 화이트리스트 CRUD 기능을 제공합니다.
 */
@Component
@RequiredArgsConstructor
@Slf4j
public class WhiteListHandler {

    private final DynamoDbClient dynamoDbClient;
    private final DynamoDBProperties dynamoDBProperties;

    /**
     * 화이트리스트에 이메일 추가
     * @param email 이메일 주소
     */
    public void saveWhiteList(String email) {
        Map<String, AttributeValue> item = new HashMap<>();
        item.put("email", AttributeValue.builder().s(email).build());

        PutItemRequest putItemRequest = PutItemRequest.builder()
                .tableName(dynamoDBProperties.getTables().getWhitelist())
                .item(item)
                .build();

        try {
            dynamoDbClient.putItem(putItemRequest);
        } catch (Exception e) {
            log.error("Error saving whitelist: {}", email, e);
            throw new RuntimeException("Failed to save whitelist", e);
        }
    }

    /**
     * 모든 화이트리스트 이메일 조회
     * @return 화이트리스트 이메일 목록
     */
    public List<String> findAllWhiteListEmails() {
        List<String> emails = new ArrayList<>();
        Map<String, AttributeValue> lastEvaluatedKey = null;

        try {
            do {
                ScanRequest.Builder scanRequestBuilder = ScanRequest.builder()
                        .tableName(dynamoDBProperties.getTables().getWhitelist());

                if (lastEvaluatedKey != null) {
                    scanRequestBuilder.exclusiveStartKey(lastEvaluatedKey);
                }

                ScanResponse response = dynamoDbClient.scan(scanRequestBuilder.build());
                
                for (Map<String, AttributeValue> item : response.items()) {
                    if (item.containsKey("email")) {
                        emails.add(item.get("email").s());
                    }
                }

                lastEvaluatedKey = response.lastEvaluatedKey();
            } while (lastEvaluatedKey != null && !lastEvaluatedKey.isEmpty());

            return emails;
        } catch (Exception e) {
            log.error("Error finding all whitelist emails", e);
            throw new RuntimeException("Failed to find all whitelist emails", e);
        }
    }

    /**
     * 화이트리스트 여부 확인
     * @param email 이메일 주소
     * @return 화이트리스트 여부
     */
    public boolean isWhiteListed(String email) {
        Map<String, AttributeValue> key = new HashMap<>();
        key.put("email", AttributeValue.builder().s(email).build());

        GetItemRequest getItemRequest = GetItemRequest.builder()
                .tableName(dynamoDBProperties.getTables().getWhitelist())
                .key(key)
                .build();

        try {
            GetItemResponse response = dynamoDbClient.getItem(getItemRequest);
            return response.hasItem();
        } catch (Exception e) {
            log.error("Error checking whitelist: {}", email, e);
            return false;
        }
    }

    /**
     * 화이트리스트에서 이메일 삭제
     * @param email 이메일 주소
     */
    public void deleteWhiteList(String email) {
        Map<String, AttributeValue> key = new HashMap<>();
        key.put("email", AttributeValue.builder().s(email).build());

        DeleteItemRequest deleteItemRequest = DeleteItemRequest.builder()
                .tableName(dynamoDBProperties.getTables().getWhitelist())
                .key(key)
                .build();

        try {
            dynamoDbClient.deleteItem(deleteItemRequest);
        } catch (Exception e) {
            log.error("Error deleting whitelist: {}", email, e);
            throw new RuntimeException("Failed to delete whitelist", e);
        }
    }
}

