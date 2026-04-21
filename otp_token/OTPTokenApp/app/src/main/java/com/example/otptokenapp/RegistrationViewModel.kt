package com.example.otptokenapp

import androidx.lifecycle.ViewModel

class RegistrationViewModel : ViewModel() {
    var generatedPinCode: String? = null
    var awaitingConfirmation: Boolean = false
    var enteredKeyPart: String? = null
}