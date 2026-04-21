package com.example.otptokenapp

import android.os.Bundle
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.Button
import android.widget.TextView
import android.widget.Toast
import androidx.fragment.app.Fragment
import java.security.SecureRandom
import android.util.Base64
import androidx.lifecycle.ViewModelProvider

class RegisterInitFragment : Fragment() {

    private lateinit var textViewPinCode: TextView
    private lateinit var buttonCopyPin: Button
    private lateinit var buttonNext: Button
    private lateinit var registrationViewModel: RegistrationViewModel

    override fun onCreateView(
        inflater: LayoutInflater, container: ViewGroup?, savedInstanceState: Bundle?
    ): View? {
        return inflater.inflate(R.layout.fragment_register_init, container, false)
    }

    override fun onViewCreated(view: View, savedInstanceState: Bundle?) {
        super.onViewCreated(view, savedInstanceState)
        registrationViewModel = ViewModelProvider(requireActivity())[RegistrationViewModel::class.java]

        textViewPinCode = view.findViewById(R.id.textViewPinCode)
        buttonCopyPin = view.findViewById(R.id.buttonCopyPin)
        buttonNext = view.findViewById(R.id.buttonNextToConfirm)

        // Если PIN-код уже сгенерирован (например, после поворота), используем его, иначе генерируем новый
        val pinCode = registrationViewModel.generatedPinCode ?: generatePinCode().also {
            registrationViewModel.generatedPinCode = it
        }
        textViewPinCode.text = pinCode

        buttonCopyPin.setOnClickListener {
            copyToClipboard(pinCode)
            Toast.makeText(requireContext(), "PIN-код скопирован", Toast.LENGTH_SHORT).show()
        }

        buttonNext.setOnClickListener {
            registrationViewModel.awaitingConfirmation = true
            (requireActivity() as MainActivity).showMainContent()
        }
    }

    private fun generatePinCode(): String {
        val randomBytes = ByteArray(6)
        SecureRandom().nextBytes(randomBytes)
        return Base64.encodeToString(
            randomBytes,
            Base64.URL_SAFE or Base64.NO_PADDING or Base64.NO_WRAP
        ).uppercase()
    }

    private fun copyToClipboard(text: String) {
        val clipboard = requireContext().getSystemService(android.content.Context.CLIPBOARD_SERVICE) as android.content.ClipboardManager
        val clip = android.content.ClipData.newPlainText("PIN code", text)
        clipboard.setPrimaryClip(clip)
    }
}