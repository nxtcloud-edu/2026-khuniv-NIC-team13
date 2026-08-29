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

import java.util.HashMap;
import java.util.Map;
import java.util.Optional;

/**
 * AccessCode 관련 DynamoDB 작업을 처리하는 핸들러
 * 이메일 인증 코드 생성/조회/삭제 기능을 제공합니다.
 */
@Component
@RequiredArgsConstructor
@Slf4j
public class AccessCodeHandler {

    private final DynamoDbClient dynamoDbClient;
    private final DynamoDBProperties dynamoDBProperties;

    /**
     * 인증 코드 조회
     * @param email 이메일 주소
     * @return 인증 코드 (만료되지 않은 경우)
     */
    public Optional<Integer> getAccessCode(String email) {
        String accessCodeKey = "access_code:" + email;

        Map<String, AttributeValue> key = new HashMap<>();
        key.put("access_code_key", AttributeValue.builder().s(accessCodeKey).build());

        GetItemRequest getItemRequest = GetItemRequest.builder()
                .tableName(dynamoDBProperties.getTables().getAccessCodes())
                .key(key)
                .build();

        try {
            GetItemResponse response = dynamoDbClient.getItem(getItemRequest);
            
            if (!response.hasItem()) {
                return Optional.empty();
            }

            Map<String, AttributeValue> item = response.item();
            
            // TTL 확인 (만료된 항목은 자동 삭제되지만, 조회 시 확인)
            if (item.containsKey("ttl")) {
                long ttl = Long.parseLong(item.get("ttl").n());
                long currentTime = System.currentTimeMillis() / 1000;
                if (ttl < currentTime) {
                    // 만료된 항목 삭제
                    deleteAccessCode(email);
                    return Optional.empty();
                }
            }

            if (item.containsKey("accessCode")) {
                int accessCode = Integer.parseInt(item.get("accessCode").n());
                return Optional.of(accessCode);
            }

            return Optional.empty();
        } catch (Exception e) {
            log.error("Error getting access code for email: {}", email, e);
            return Optional.empty();
        }
    }

    /**
     * 인증 코드 생성
     * @param email 이메일 주소
     * @param duration 유효 시간(분)
     * @return 생성된 인증 코드
     */
    public int createAccessCode(String email, int duration) {
        String accessCodeKey = "access_code:" + email;
        int accessCode = createRandomNumber();
        long ttl = System.currentTimeMillis() / 1000 + (duration * 60L);

        Map<String, AttributeValue> item = new HashMap<>();
        // #region agent log
        log.info("[DEBUG] createAccessCode - accessCodeKey: {}, tableName: {}", accessCodeKey, dynamoDBProperties.getTables().getAccessCodes());
        // #endregion
        item.put("access_code_key", AttributeValue.builder().s(accessCodeKey).build());
        item.put("accessCode", AttributeValue.builder().n(String.valueOf(accessCode)).build());
        item.put("ttl", AttributeValue.builder().n(String.valueOf(ttl)).build());

        PutItemRequest putItemRequest = PutItemRequest.builder()
                .tableName(dynamoDBProperties.getTables().getAccessCodes())
                .item(item)
                .build();

        try {
            dynamoDbClient.putItem(putItemRequest);
            // #region agent log
            log.info("[DEBUG] createAccessCode SUCCESS - email: {}, accessCode: {}", email, accessCode);
            // #endregion
            return accessCode;
        } catch (Exception e) {
            log.error("Error creating access code for email: {}", email, e);
            throw new RuntimeException("Failed to create access code", e);
        }
    }

    /**
     * 인증 코드 삭제
     * @param email 이메일 주소
     */
    public void deleteAccessCode(String email) {
        String accessCodeKey = "access_code:" + email;

        Map<String, AttributeValue> key = new HashMap<>();
        key.put("access_code_key", AttributeValue.builder().s(accessCodeKey).build());

        DeleteItemRequest deleteItemRequest = DeleteItemRequest.builder()
                .tableName(dynamoDBProperties.getTables().getAccessCodes())
                .key(key)
                .build();

        try {
            dynamoDbClient.deleteItem(deleteItemRequest);
        } catch (Exception e) {
            log.error("Error deleting access code for email: {}", email, e);
            throw new RuntimeException("Failed to delete access code", e);
        }
    }

    private int createRandomNumber() {
        return (int) ((Math.random() * 900000) + 100000);
    }
}

