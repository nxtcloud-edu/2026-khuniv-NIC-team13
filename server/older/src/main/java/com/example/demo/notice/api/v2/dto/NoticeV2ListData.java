package com.example.demo.notice.api.v2.dto;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.util.List;

@Data
@NoArgsConstructor
@AllArgsConstructor
public class NoticeV2ListData {
    private List<NoticeV2ListItemDto> notices;
    private long total;
    private int page;
}
