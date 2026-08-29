package com.example.demo.notice.api.v2.dto;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.LocalDateTime;

@Data
@NoArgsConstructor
@AllArgsConstructor
public class NoticeV2PatchData {
    private Long id;
    private String title;
    private LocalDateTime modifiedAt;
}
