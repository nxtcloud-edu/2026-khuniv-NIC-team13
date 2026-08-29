package com.example.demo.shared.web.v2.response;

import com.fasterxml.jackson.annotation.JsonInclude;
import io.swagger.v3.oas.annotations.media.Schema;
import lombok.Getter;

@Getter
@JsonInclude(JsonInclude.Include.ALWAYS)
@Schema(description = "v2 API 공통 응답 래퍼. success=true면 data에 페이로드, false면 data=null.")
public abstract class BaseResponse<T> {

    @Schema(description = "요청 성공 여부", example = "true")
    private final boolean success;
    @Schema(description = "응답 코드. 성공은 SUCCESS/CREATED, 실패는 서술형(예: INVALID_ACCESS_CODE)", example = "SUCCESS")
    private final String code;
    @Schema(description = "응답 메시지", example = "요청이 성공적으로 처리되었습니다.")
    private final String message;
    @Schema(description = "페이로드. 실패 시 null")
    private final T data;

    protected BaseResponse(boolean success, String code, String message, T data) {
        this.success = success;
        this.code = code;
        this.message = message;
        this.data = data;
    }
}
