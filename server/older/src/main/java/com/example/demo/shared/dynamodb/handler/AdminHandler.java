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
 * Admin 관련 DynamoDB 작업을 처리하는 핸들러
 * 관리자 CRUD 기능을 제공합니다.
 */
@Component
@RequiredArgsConstructor
@Slf4j
public class AdminHandler {

    private final DynamoDbClient dynamoDbClient;
    private final DynamoDBProperties dynamoDBProperties;

    private boolean isMetricKey(String emailKey) {
        return emailKey != null && emailKey.startsWith("__METRIC_");
    }

    /**
     * 관리자 저장
     * @param email 관리자 이메일
     */
    public void saveAdmin(String email) {
        Map<String, AttributeValue> item = new HashMap<>();
        item.put("email", AttributeValue.builder().s(email).build());

        PutItemRequest putItemRequest = PutItemRequest.builder()
                .tableName(dynamoDBProperties.getTables().getAdmins())
                .item(item)
                .build();

        try {
            dynamoDbClient.putItem(putItemRequest);
        } catch (Exception e) {
            log.error("Error saving admin: {}", email, e);
            throw new RuntimeException("Failed to save admin", e);
        }
    }

    /**
     * 모든 관리자 이메일 조회
     * @return 관리자 이메일 목록
     */
    public List<String> findAllAdminEmails() {
        List<String> emails = new ArrayList<>();
        Map<String, AttributeValue> lastEvaluatedKey = null;

        try {
            do {
                ScanRequest.Builder scanRequestBuilder = ScanRequest.builder()
                        .tableName(dynamoDBProperties.getTables().getAdmins());

                if (lastEvaluatedKey != null) {
                    scanRequestBuilder.exclusiveStartKey(lastEvaluatedKey);
                }

                ScanResponse response = dynamoDbClient.scan(scanRequestBuilder.build());
                
                for (Map<String, AttributeValue> item : response.items()) {
                    if (item.containsKey("email")) {
                        String email = item.get("email").s();
                        // metrics 전용 특수 키는 관리자 목록에서 제외
                        if (!isMetricKey(email)) {
                            emails.add(email);
                        }
                    }
                }

                lastEvaluatedKey = response.lastEvaluatedKey();
            } while (lastEvaluatedKey != null && !lastEvaluatedKey.isEmpty());

            return emails;
        } catch (Exception e) {
            log.error("Error finding all admin emails", e);
            throw new RuntimeException("Failed to find all admin emails", e);
        }
    }

    /**
     * 관리자 여부 확인
     * @param email 이메일 주소
     * @return 관리자 여부
     */
    public boolean isAdmin(String email) {
        if (isMetricKey(email)) {
            return false;
        }
        Map<String, AttributeValue> key = new HashMap<>();
        key.put("email", AttributeValue.builder().s(email).build());

        GetItemRequest getItemRequest = GetItemRequest.builder()
                .tableName(dynamoDBProperties.getTables().getAdmins())
                .key(key)
                .build();

        try {
            GetItemResponse response = dynamoDbClient.getItem(getItemRequest);
            return response.hasItem();
        } catch (Exception e) {
            log.error("Error checking admin: {}", email, e);
            return false;
        }
    }

    /**
     * 관리자 삭제
     * @param email 관리자 이메일
     */
    public void deleteAdmin(String email) {
        Map<String, AttributeValue> key = new HashMap<>();
        key.put("email", AttributeValue.builder().s(email).build());

        DeleteItemRequest deleteItemRequest = DeleteItemRequest.builder()
                .tableName(dynamoDBProperties.getTables().getAdmins())
                .key(key)
                .build();

        try {
            dynamoDbClient.deleteItem(deleteItemRequest);
        } catch (Exception e) {
            log.error("Error deleting admin: {}", email, e);
            throw new RuntimeException("Failed to delete admin", e);
        }
    }
}

