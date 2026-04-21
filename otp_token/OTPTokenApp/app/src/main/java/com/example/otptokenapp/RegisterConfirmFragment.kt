package com.example.otptokenapp

import android.os.Bundle
import android.text.Editable
import android.text.TextWatcher
import android.util.Log
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.Button
import android.widget.EditText
import android.widget.Toast
import androidx.biometric.BiometricPrompt
import androidx.core.content.ContextCompat
import androidx.core.content.edit
import androidx.fragment.app.Fragment
import androidx.lifecycle.ViewModelProvider
import java.util.concurrent.Executor
import javax.crypto.Cipher
import javax.crypto.SecretKey

class RegisterConfirmFragment : Fragment() {

    private lateinit var editTextKeyPart: EditText
    private lateinit var buttonConfirm: Button
    private lateinit var registrationViewModel: RegistrationViewModel
    private lateinit var executor: Executor
    private lateinit var biometricPrompt: BiometricPrompt
    private lateinit var promptInfo: BiometricPrompt.PromptInfo
    private var userKeyToEncrypt: ByteArray? = null
    private var masterKeyCached: SecretKey? = null
    private var cipherForUserKey: Cipher? = null

    override fun onCreateView(
        inflater: LayoutInflater, container: ViewGroup?, savedInstanceState: Bundle?
    ): View? {
        return inflater.inflate(R.layout.fragment_register_confirm, container, false)
    }

    override fun onViewCreated(view: View, savedInstanceState: Bundle?) {
        super.onViewCreated(view, savedInstanceState)

        registrationViewModel = ViewModelProvider(requireActivity())[RegistrationViewModel::class.java]

        editTextKeyPart = view.findViewById(R.id.editTextKeyPart)
        buttonConfirm = view.findViewById(R.id.buttonConfirm)

        editTextKeyPart.setText(registrationViewModel.enteredKeyPart ?: "")
        editTextKeyPart.addTextChangedListener(object : TextWatcher {
            override fun beforeTextChanged(s: CharSequence?, start: Int, count: Int, after: Int) {}
            override fun onTextChanged(s: CharSequence?, start: Int, before: Int, count: Int) {}
            override fun afterTextChanged(s: Editable?) {
                registrationViewModel.enteredKeyPart = s?.toString()
            }
        })

        setupBiometricPrompt()

        buttonConfirm.setOnClickListener {
            val keyPart = editTextKeyPart.text.toString().trim()
            if (keyPart.isEmpty()) {
                Toast.makeText(requireContext(), "Введите key_part", Toast.LENGTH_SHORT).show()
                return@setOnClickListener
            }
            registrationViewModel.enteredKeyPart = keyPart
            val pinCode = registrationViewModel.generatedPinCode
            if (pinCode == null) {
                Toast.makeText(requireContext(), "Ошибка: PIN-код не найден", Toast.LENGTH_SHORT).show()
                return@setOnClickListener
            }
            userKeyToEncrypt = "$keyPart:$pinCode".toByteArray()
            startEncryptionWithBiometrics()
        }
    }

    private fun startEncryptionWithBiometrics() {
        try {
            val masterKey = CryptoHelper.getMasterKey(requireContext())
            masterKeyCached = masterKey
            cipherForUserKey = Cipher.getInstance("AES/GCM/NoPadding").apply {
                init(Cipher.ENCRYPT_MODE, masterKey)
            }
            val cryptoObject = BiometricPrompt.CryptoObject(cipherForUserKey!!)
            biometricPrompt.authenticate(promptInfo, cryptoObject)
        } catch (e: Exception) {
            Log.e("OTP_ERROR", "Failed to init cipher", e)
            Toast.makeText(requireContext(), "Ошибка подготовки шифрования: ${e.message}", Toast.LENGTH_LONG).show()
        }
    }

    private fun setupBiometricPrompt() {
        executor = ContextCompat.getMainExecutor(requireContext())
        biometricPrompt = BiometricPrompt(this, executor,
            object : BiometricPrompt.AuthenticationCallback() {
                override fun onAuthenticationSucceeded(result: BiometricPrompt.AuthenticationResult) {
                    super.onAuthenticationSucceeded(result)
                    if (cipherForUserKey != null && userKeyToEncrypt != null) {
                        try {
                            // Объединяем данные: userKey + разделитель + loginCount
                            val loginCountBytes = "0".toByteArray()
                            val separator = "|".toByteArray()
                            val combined = userKeyToEncrypt!! + separator + loginCountBytes
                            val encryptedData = cipherForUserKey!!.doFinal(combined)
                            saveEncryptedData(encryptedData)
                        } catch (e: Exception) {
                            Log.e("OTP_ERROR", "Encryption failed", e)
                            Toast.makeText(requireContext(), "Ошибка шифрования: ${e.message}", Toast.LENGTH_LONG).show()
                            requireActivity().finishAffinity()
                        }
                    } else {
                        Toast.makeText(requireContext(), "Криптообъект не получен", Toast.LENGTH_SHORT).show()
                    }
                }

                override fun onAuthenticationError(errorCode: Int, errString: CharSequence) {
                    super.onAuthenticationError(errorCode, errString)
                    Toast.makeText(requireContext(), "Ошибка биометрии: $errString", Toast.LENGTH_SHORT).show()
                }

                override fun onAuthenticationFailed() {
                    super.onAuthenticationFailed()
                    Toast.makeText(requireContext(), "Отпечаток не распознан", Toast.LENGTH_SHORT).show()
                }
            })

        promptInfo = BiometricPrompt.PromptInfo.Builder()
            .setTitle("Подтверждение регистрации")
            .setSubtitle("Требуется отпечаток пальца для завершения регистрации")
            .setNegativeButtonText("Отмена")
            .build()
    }

    private fun saveEncryptedData(encryptedData: ByteArray) {
        val prefs = requireContext().getSharedPreferences("secure_prefs", android.content.Context.MODE_PRIVATE)
        prefs.edit {
            putString("encrypted_data", android.util.Base64.encodeToString(encryptedData, android.util.Base64.DEFAULT))
            putBoolean("is_registered", true)
        }
        Toast.makeText(requireContext(), R.string.saving_success, Toast.LENGTH_LONG).show()
        (requireActivity() as MainActivity).showMainOtpScreen()
    }
}