package com.example.demo.email.infra;


import com.example.demo.email.domain.Email;

import java.util.List;

public interface EmailRepository{
    Email findByEmail(String email);

    Email save(Email email);

    void deleteAll();


    List<Email> findAll();

}
