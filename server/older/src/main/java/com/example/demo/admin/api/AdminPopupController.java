package com.example.demo.admin.api;

import com.example.demo.shared.dynamodb.handler.PopupHandler;
import lombok.Data;
import lombok.RequiredArgsConstructor;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.stereotype.Controller;
import org.springframework.ui.Model;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.multipart.MultipartFile;

import java.io.IOException;
import java.util.Optional;

@Controller
@RequiredArgsConstructor
public class AdminPopupController {

    private final PopupHandler popupHandler;

    @GetMapping("/admin/popup/form")
    String popupForm(@CookieValue String loginStatus, Model model) {
        Optional<PopupHandler.PopupData> popupOpt = popupHandler.getPopup();
        Popup popup = null;
        if (popupOpt.isPresent()) {
            PopupHandler.PopupData popupData = popupOpt.get();
            popup = new Popup();
            popup.setTitle(popupData.getTitle());
            popup.setLink(popupData.getLink());
            popup.setImage(popupData.getImage());
        }
        model.addAttribute("popup", popup);
        return "popup-form";
    }

    @GetMapping("/admin/popup/image")
    @ResponseBody
    public ResponseEntity<byte[]> getPopupImage() {
        Optional<PopupHandler.PopupData> popupOpt = popupHandler.getPopup();
        
        if (popupOpt.isEmpty() || popupOpt.get().getImage() == null) {
            return ResponseEntity.notFound().build();
        }

        return ResponseEntity.ok()
                .contentType(MediaType.IMAGE_PNG) // 업로드한 타입 맞춰주기
                .body(popupOpt.get().getImage());
    }

    @PostMapping("/admin/popup/form")
    String postPopup(@CookieValue String loginStatus,
                     @RequestParam String title,
                     @RequestParam(defaultValue = "") String link,
                     @RequestParam MultipartFile image) throws IOException {

        popupHandler.deletePopup();
        popupHandler.savePopup(title, link, image.getBytes());

        return "redirect:/admin/popup/form";
    }

    @Data
    static class Popup {
        private String title;
        private String link;
        private byte[] image;
    }
}
