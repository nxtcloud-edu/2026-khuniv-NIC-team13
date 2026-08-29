package com.example.demo.notice.api.v2.dto;

import lombok.Data;

@Data
public class NoticeV2UpdateRequest {
    private String title;
    private String content;
}
