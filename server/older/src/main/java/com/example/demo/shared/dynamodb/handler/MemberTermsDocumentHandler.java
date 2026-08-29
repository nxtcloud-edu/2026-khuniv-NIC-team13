package com.example.demo.shared.dynamodb.handler;

import com.example.demo.config.DynamoDBProperties;
import lombok.RequiredArgsConstructor;
import lombok.Value;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Component;
import software.amazon.awssdk.services.dynamodb.DynamoDbClient;
import software.amazon.awssdk.services.dynamodb.model.AttributeValue;
import software.amazon.awssdk.services.dynamodb.model.GetItemRequest;
import software.amazon.awssdk.services.dynamodb.model.GetItemResponse;
import software.amazon.awssdk.services.dynamodb.model.PutItemRequest;

import java.time.Instant;
import java.util.HashMap;
import java.util.Map;
import java.util.Optional;

/**
 * 멤버 약관 동의 문서를 DynamoDB에 멤버당 1건 저장합니다.
 *
 * Key:
 * - pk: MEMBER#{memberKey}
 * - sk: TERMS
 */
@Component
@RequiredArgsConstructor
@Slf4j
public class MemberTermsDocumentHandler {

    public static final String SK_TERMS = "TERMS";

    private final DynamoDbClient dynamoDbClient;
    private final DynamoDBProperties dynamoDBProperties;

    public Optional<MemberTermsDocument> getTerms(String memberKey) {
        Map<String, AttributeValue> key = new HashMap<>();
        key.put("pk", AttributeValue.builder().s(toPk(memberKey)).build());
        key.put("sk", AttributeValue.builder().s(SK_TERMS).build());

        GetItemRequest request = GetItemRequest.builder()
                .tableName(dynamoDBProperties.getTables().getMemberDocuments())
                .key(key)
                .build();

        try {
            GetItemResponse response = dynamoDbClient.getItem(request);
            if (!response.hasItem()) {
                return Optional.empty();
            }
            return Optional.of(mapToDocument(response.item()));
        } catch (Exception e) {
            log.error("Error getting member terms memberKey={}", memberKey, e);
            return Optional.empty();
        }
    }

    /**
     * 문서를 upsert 합니다. createdAt은 기존 값이 있으면 유지합니다.
     */
    public MemberTermsDocument upsertTerms(
            String memberKey,
            Agreements agreements,
            Instant now,
            TermsVersions versions
    ) {
        String pk = toPk(memberKey);

        String createdAt = getTerms(memberKey)
                .map(MemberTermsDocument::getCreatedAt)
                .orElse(now.toString());

        MemberTermsDocument doc = new MemberTermsDocument(
                pk,
                SK_TERMS,
                buildAgreementsAttribute(agreements, now, versions),
                createdAt,
                now.toString()
        );

        Map<String, AttributeValue> item = new HashMap<>();
        item.put("pk", AttributeValue.builder().s(doc.pk).build());
        item.put("sk", AttributeValue.builder().s(doc.sk).build());
        item.put("agreements", doc.agreements);
        item.put("createdAt", AttributeValue.builder().s(doc.createdAt).build());
        item.put("updatedAt", AttributeValue.builder().s(doc.updatedAt).build());

        PutItemRequest request = PutItemRequest.builder()
                .tableName(dynamoDBProperties.getTables().getMemberDocuments())
                .item(item)
                .build();

        dynamoDbClient.putItem(request);
        return doc;
    }

    private static String toPk(String memberKey) {
        return "MEMBER#" + memberKey;
    }

    private static AttributeValue buildAgreementsAttribute(Agreements agreements, Instant now, TermsVersions versions) {
        Map<String, AttributeValue> root = new HashMap<>();
        root.put("termsOfService", buildAgreementItem(agreements.termsOfServiceAgreed, now, versions.termsVersion));
        root.put("privacyCollection", buildAgreementItem(agreements.privacyCollectionAgreed, now, versions.privacyCollectionVersion));
        root.put("privacyPolicy", buildAgreementItem(agreements.privacyPolicyAgreed, now, versions.privacyPolicyVersion));
        root.put("thirdPartySharing", buildAgreementItem(agreements.thirdPartySharingAgreed, now, versions.thirdPartySharingVersion));
        return AttributeValue.builder().m(root).build();
    }

    private static AttributeValue buildAgreementItem(boolean agreed, Instant now, String version) {
        Map<String, AttributeValue> m = new HashMap<>();
        m.put("agreed", AttributeValue.builder().bool(agreed).build());
        if (agreed) {
            m.put("agreedAt", AttributeValue.builder().s(now.toString()).build());
        }
        m.put("version", AttributeValue.builder().s(version).build());
        return AttributeValue.builder().m(m).build();
    }

    private static MemberTermsDocument mapToDocument(Map<String, AttributeValue> item) {
        AttributeValue agreements = item.get("agreements");
        String createdAt = item.containsKey("createdAt") ? item.get("createdAt").s() : null;
        String updatedAt = item.containsKey("updatedAt") ? item.get("updatedAt").s() : null;
        return new MemberTermsDocument(
                item.get("pk").s(),
                item.get("sk").s(),
                agreements,
                createdAt,
                updatedAt
        );
    }

    @Value
    public static class Agreements {
        boolean termsOfServiceAgreed;
        boolean privacyCollectionAgreed;
        boolean privacyPolicyAgreed;
        boolean thirdPartySharingAgreed;
    }

    @Value
    public static class TermsVersions {
        String termsVersion;
        String privacyCollectionVersion;
        String privacyPolicyVersion;
        String thirdPartySharingVersion;
    }

    @Value
    public static class MemberTermsDocument {
        String pk;
        String sk;
        AttributeValue agreements;
        String createdAt;
        String updatedAt;
    }
}

