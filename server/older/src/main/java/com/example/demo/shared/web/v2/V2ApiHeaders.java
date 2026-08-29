package com.example.demo.shared.web.v2;

/**
 * v2 API는 {@code X-API-Version: 2} 헤더가 있을 때만 매핑됩니다.
 */
public final class V2ApiHeaders {

    public static final String NAME = "X-API-Version";
    public static final String VALUE = "2";

    /** {@link org.springframework.web.bind.annotation.RequestMapping#headers()} 조건 */
    public static final String MAPPING_CONDITION = NAME + "=" + VALUE;

    private V2ApiHeaders() {
    }
}
