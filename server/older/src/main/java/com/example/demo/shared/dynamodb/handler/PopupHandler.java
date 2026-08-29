package com.example.demo.shared.dynamodb.handler;

import com.example.demo.config.DynamoDBProperties;
import lombok.Data;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Component;
import software.amazon.awssdk.services.dynamodb.DynamoDbClient;
import software.amazon.awssdk.services.dynamodb.model.AttributeValue;
import software.amazon.awssdk.services.dynamodb.model.DeleteItemRequest;
import software.amazon.awssdk.services.dynamodb.model.GetItemRequest;
import software.amazon.awssdk.services.dynamodb.model.GetItemResponse;
import software.amazon.awssdk.services.dynamodb.model.PutItemRequest;

import java.util.Base64;
import java.util.HashMap;
import java.util.Map;
import java.util.Optional;

/**
 * Popup 관련 DynamoDB 작업을 처리하는 핸들러
 * 팝업 데이터 CRUD 기능을 제공합니다.
 */
@Component
@RequiredArgsConstructor
@Slf4j
public class PopupHandler {

    private final DynamoDbClient dynamoDbClient;
    private final DynamoDBProperties dynamoDBProperties;

    /**
     * 팝업 데이터 조회
     * @return 팝업 데이터
     */
    public Optional<PopupData> getPopup() {
        Map<String, AttributeValue> key = new HashMap<>();
        key.put("id", AttributeValue.builder().s("popup").build());

        GetItemRequest getItemRequest = GetItemRequest.builder()
                .tableName(dynamoDBProperties.getTables().getPopups())
                .key(key)
                .build();

        try {
            GetItemResponse response = dynamoDbClient.getItem(getItemRequest);
            
            if (!response.hasItem()) {
                return Optional.empty();
            }

            Map<String, AttributeValue> item = response.item();
            PopupData popup = new PopupData();
            
            if (item.containsKey("title")) {
                popup.setTitle(item.get("title").s());
            }
            if (item.containsKey("link")) {
                popup.setLink(item.get("link").s());
            }
            if (item.containsKey("image")) {
                // Base64 디코딩
                String base64Image = item.get("image").s();
                popup.setImage(Base64.getDecoder().decode(base64Image));
            }

            return Optional.of(popup);
        } catch (Exception e) {
            log.error("Error getting popup", e);
            return Optional.empty();
        }
    }

    /**
     * 팝업 저장
     * @param title 팝업 제목
     * @param link 팝업 링크
     * @param image 팝업 이미지 바이트 배열
     */
    public void savePopup(String title, String link, byte[] image) {
        Map<String, AttributeValue> item = new HashMap<>();
        item.put("id", AttributeValue.builder().s("popup").build());
        item.put("title", AttributeValue.builder().s(title).build());
        item.put("link", AttributeValue.builder().s(link != null ? link : "").build());
        
        // 이미지를 Base64로 인코딩
        String base64Image = Base64.getEncoder().encodeToString(image);
        item.put("image", AttributeValue.builder().s(base64Image).build());

        PutItemRequest putItemRequest = PutItemRequest.builder()
                .tableName(dynamoDBProperties.getTables().getPopups())
                .item(item)
                .build();

        try {
            dynamoDbClient.putItem(putItemRequest);
        } catch (Exception e) {
            log.error("Error saving popup", e);
            throw new RuntimeException("Failed to save popup", e);
        }
    }

    /**
     * 팝업 삭제
     */
    public void deletePopup() {
        Map<String, AttributeValue> key = new HashMap<>();
        key.put("id", AttributeValue.builder().s("popup").build());

        DeleteItemRequest deleteItemRequest = DeleteItemRequest.builder()
                .tableName(dynamoDBProperties.getTables().getPopups())
                .key(key)
                .build();

        try {
            dynamoDbClient.deleteItem(deleteItemRequest);
        } catch (Exception e) {
            log.error("Error deleting popup", e);
            throw new RuntimeException("Failed to delete popup", e);
        }
    }

    /**
     * 팝업 데이터 DTO
     */
    @Data
    public static class PopupData {
        private String title;
        private String link;
        private byte[] image;
    }
}

