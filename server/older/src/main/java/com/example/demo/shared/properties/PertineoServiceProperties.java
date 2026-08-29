package com.example.demo.shared.properties;

import com.example.demo.shared.cache.LocalCacheService;
import com.example.demo.shared.properties.domain.Properties;
import jakarta.annotation.PostConstruct;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Component;

import java.util.List;

/**
 * Pertineo 서비스 설정 관리
 * LocalCacheService를 통해 캐시된 설정 데이터를 제공합니다.
 */
@Component
@RequiredArgsConstructor
@Slf4j
public class PertineoServiceProperties {

    private final LocalCacheService localCacheService;

    @PostConstruct
    public void init(){
        // 캐시 초기화 (선택적 - 첫 조회 시 자동 로드됨)
        log.info("PertineoServiceProperties 초기화 완료 - 캐시 기반 설정 사용");
    }

    /**
     * 관리자 이메일 목록 조회
     * @return 관리자 이메일 리스트 (캐시됨, TTL 30분)
     */
    public List<String> getAdminList(){
        return localCacheService.getAdminList();
    }

    /**
     * 화이트리스트 이메일 목록 조회
     * @return 화이트리스트 이메일 리스트 (캐시됨, TTL 30분)
     */
    public List<String> getWhiteList(){
        return localCacheService.getWhiteList();
    }

    /**
     * 일일 최대 인증코드 발급 횟수
     * @return 최대 횟수 (null일 수 있음)
     */
    public Integer getAccessCodePerDay(){
        return localCacheService.getProperties()
                .map(Properties::getMaxAccessCodePerDay)
                .orElse(null);
    }

    /**
     * 일일 최대 분석 횟수
     * @return 최대 횟수 (null일 수 있음)
     */
    public Integer getAnalysisPerDay(){
        return localCacheService.getProperties()
                .map(Properties::getMaxAnalysisPerDay)
                .orElse(null);
    }

    /**
     * 설정 캐시 수동 갱신
     * 관리자 페이지에서 설정 변경 후 호출
     */
    public void updateProperties(){
        localCacheService.refreshConfigCache();
        log.info("설정 캐시 갱신 완료");
    }

}
