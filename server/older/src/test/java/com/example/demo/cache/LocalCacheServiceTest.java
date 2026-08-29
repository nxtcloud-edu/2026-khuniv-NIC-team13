package com.example.demo.cache;

import com.example.demo.config.CacheConfig;
import com.example.demo.shared.cache.LocalCacheService;
import com.example.demo.shared.dynamodb.handler.AdminHandler;
import com.example.demo.shared.dynamodb.handler.PropertiesHandler;
import com.example.demo.shared.dynamodb.handler.WhiteListHandler;
import com.example.demo.shared.properties.domain.Properties;
import com.github.benmanes.caffeine.cache.Cache;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

import java.util.Arrays;
import java.util.List;
import java.util.Optional;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.Mockito.*;

/**
 * LocalCacheService 단위 테스트
 */
@ExtendWith(MockitoExtension.class)
class LocalCacheServiceTest {

    @Mock
    private AdminHandler adminHandler;

    @Mock
    private WhiteListHandler whiteListHandler;

    @Mock
    private PropertiesHandler propertiesHandler;

    private LocalCacheService localCacheService;
    private CacheConfig cacheConfig;

    @BeforeEach
    void setUp() {
        cacheConfig = new CacheConfig();
        Cache<String, Integer> dailyLimitCache = cacheConfig.dailyLimitCache();
        Cache<String, List<String>> configListCache = cacheConfig.configListCache();
        Cache<String, Object> propertiesCache = cacheConfig.propertiesCache();

        localCacheService = new LocalCacheService(
                dailyLimitCache,
                configListCache,
                propertiesCache,
                adminHandler,
                whiteListHandler,
                propertiesHandler
        );
    }

    // === 일일 사용량 제한 테스트 ===

    @Test
    void testGetDailyCount_초기값은_0() {
        // Given
        String email = "test@example.com";
        String limitType = "accessCode";

        // When
        int count = localCacheService.getDailyCount(email, limitType);

        // Then
        assertEquals(0, count);
    }

    @Test
    void testIncrementDailyCount_증가_동작() {
        // Given
        String email = "test@example.com";
        String limitType = "accessCode";

        // When
        int count1 = localCacheService.incrementDailyCount(email, limitType);
        int count2 = localCacheService.incrementDailyCount(email, limitType);
        int count3 = localCacheService.incrementDailyCount(email, limitType);

        // Then
        assertEquals(1, count1);
        assertEquals(2, count2);
        assertEquals(3, count3);
    }

    @Test
    void testSetDailyCount_값_설정() {
        // Given
        String email = "test@example.com";
        String limitType = "analysis";

        // When
        localCacheService.setDailyCount(email, limitType, 5);
        int count = localCacheService.getDailyCount(email, limitType);

        // Then
        assertEquals(5, count);
    }

    @Test
    void testResetDailyCount_특정_키_초기화() {
        // Given
        String email = "test@example.com";
        String limitType = "accessCode";
        localCacheService.setDailyCount(email, limitType, 10);

        // When
        localCacheService.resetDailyCount(email, limitType);
        int count = localCacheService.getDailyCount(email, limitType);

        // Then
        assertEquals(0, count);
    }

    @Test
    void testResetAllDailyLimits_전체_초기화() {
        // Given
        localCacheService.setDailyCount("user1@test.com", "accessCode", 5);
        localCacheService.setDailyCount("user2@test.com", "analysis", 3);

        // When
        localCacheService.resetAllDailyLimits();

        // Then
        assertEquals(0, localCacheService.getDailyCount("user1@test.com", "accessCode"));
        assertEquals(0, localCacheService.getDailyCount("user2@test.com", "analysis"));
    }

    @Test
    void testDifferentLimitTypes_독립적으로_관리() {
        // Given
        String email = "test@example.com";

        // When
        localCacheService.incrementDailyCount(email, "accessCode");
        localCacheService.incrementDailyCount(email, "accessCode");
        localCacheService.incrementDailyCount(email, "analysis");

        // Then
        assertEquals(2, localCacheService.getDailyCount(email, "accessCode"));
        assertEquals(1, localCacheService.getDailyCount(email, "analysis"));
    }

    // === 설정 캐시 테스트 ===

    @Test
    void testGetAdminList_캐시_동작() {
        // Given
        List<String> adminEmails = Arrays.asList("admin1@test.com", "admin2@test.com");
        when(adminHandler.findAllAdminEmails()).thenReturn(adminEmails);

        // When
        List<String> result1 = localCacheService.getAdminList();
        List<String> result2 = localCacheService.getAdminList();

        // Then
        assertEquals(adminEmails, result1);
        assertEquals(adminEmails, result2);
        // DynamoDB는 한 번만 호출되어야 함 (캐시 히트)
        verify(adminHandler, times(1)).findAllAdminEmails();
    }

    @Test
    void testGetWhiteList_캐시_동작() {
        // Given
        List<String> whiteListEmails = Arrays.asList("user1@test.com", "user2@test.com");
        when(whiteListHandler.findAllWhiteListEmails()).thenReturn(whiteListEmails);

        // When
        List<String> result1 = localCacheService.getWhiteList();
        List<String> result2 = localCacheService.getWhiteList();

        // Then
        assertEquals(whiteListEmails, result1);
        assertEquals(whiteListEmails, result2);
        verify(whiteListHandler, times(1)).findAllWhiteListEmails();
    }

    @Test
    void testGetProperties_캐시_동작() {
        // Given
        Properties properties = new Properties();
        properties.setMaxAccessCodePerDay(10);
        properties.setMaxAnalysisPerDay(5);
        when(propertiesHandler.findProperties()).thenReturn(Optional.of(properties));

        // When
        Optional<Properties> result1 = localCacheService.getProperties();
        Optional<Properties> result2 = localCacheService.getProperties();

        // Then
        assertTrue(result1.isPresent());
        assertEquals(10, result1.get().getMaxAccessCodePerDay());
        assertEquals(5, result1.get().getMaxAnalysisPerDay());
        verify(propertiesHandler, times(1)).findProperties();
    }

    @Test
    void testRefreshConfigCache_캐시_무효화() {
        // Given
        List<String> adminEmails = Arrays.asList("admin@test.com");
        when(adminHandler.findAllAdminEmails()).thenReturn(adminEmails);
        
        localCacheService.getAdminList(); // 캐시에 로드

        // When
        localCacheService.refreshConfigCache();
        localCacheService.getAdminList(); // 다시 조회

        // Then - DynamoDB가 두 번 호출되어야 함
        verify(adminHandler, times(2)).findAllAdminEmails();
    }

    @Test
    void testRefreshAdminCache_관리자_캐시만_무효화() {
        // Given
        when(adminHandler.findAllAdminEmails()).thenReturn(Arrays.asList("admin@test.com"));
        when(whiteListHandler.findAllWhiteListEmails()).thenReturn(Arrays.asList("user@test.com"));

        localCacheService.getAdminList();
        localCacheService.getWhiteList();

        // When
        localCacheService.refreshAdminCache();
        localCacheService.getAdminList();
        localCacheService.getWhiteList();

        // Then
        verify(adminHandler, times(2)).findAllAdminEmails(); // 무효화 후 재조회
        verify(whiteListHandler, times(1)).findAllWhiteListEmails(); // 캐시 히트
    }

    // === 예외 처리 테스트 ===

    @Test
    void testGetAdminList_DynamoDB_오류시_빈_리스트_반환() {
        // Given
        when(adminHandler.findAllAdminEmails()).thenThrow(new RuntimeException("DynamoDB error"));

        // When
        List<String> result = localCacheService.getAdminList();

        // Then
        assertNotNull(result);
        assertTrue(result.isEmpty());
    }

    @Test
    void testGetProperties_DynamoDB_오류시_empty_반환() {
        // Given
        when(propertiesHandler.findProperties()).thenThrow(new RuntimeException("DynamoDB error"));

        // When
        Optional<Properties> result = localCacheService.getProperties();

        // Then
        assertTrue(result.isEmpty());
    }
}

