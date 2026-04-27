package com.example.otptokenapp

import android.app.AlertDialog
import android.os.Bundle
import android.util.Log
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.Button
import android.widget.EditText
import android.widget.LinearLayout
import android.widget.ProgressBar
import android.widget.TextView
import android.widget.Toast
import androidx.biometric.BiometricPrompt
import androidx.core.content.ContextCompat
import androidx.core.content.edit
import androidx.fragment.app.Fragment
import java.util.concurrent.Executor

class MainOtpFragment : Fragment() {

    private lateinit var editTextChallenge: EditText
    private lateinit var buttonGenerateOtp: Button
    private lateinit var textViewOtpResult: TextView
    private lateinit var buttonReset: Button
    private lateinit var progressBarOtp: ProgressBar
    private lateinit var actionButtonsLayout: LinearLayout
    private lateinit var buttonConfirmLogin: Button
    private lateinit var buttonCancelLogin: Button

    private lateinit var executor: Executor
    private lateinit var biometricPrompt: BiometricPrompt
    private lateinit var promptInfo: BiometricPrompt.PromptInfo
    private lateinit var buttonCopyOtp: Button

    override fun onCreateView(
        inflater: LayoutInflater, container: ViewGroup?, savedInstanceState: Bundle?
    ): View {
        return inflater.inflate(R.layout.fragment_main_otp, container, false)
    }

    override fun onViewCreated(view: View, savedInstanceState: Bundle?) {
        super.onViewCreated(view, savedInstanceState)

        editTextChallenge = view.findViewById(R.id.editTextChallenge)
        buttonGenerateOtp = view.findViewById(R.id.buttonGenerateOtp)
        textViewOtpResult = view.findViewById(R.id.textViewOtpResult)
        buttonReset = view.findViewById(R.id.buttonReset)
        progressBarOtp = view.findViewById(R.id.progressBarOtp)
        actionButtonsLayout = view.findViewById(R.id.actionButtonsLayout)
        buttonConfirmLogin = view.findViewById(R.id.buttonConfirmLogin)
        buttonCancelLogin = view.findViewById(R.id.buttonCancelLogin)
        buttonCopyOtp = view.findViewById(R.id.buttonCopyOtp)
        setupBiometricPrompt()

        buttonCopyOtp.setOnClickListener {
            val otpText = textViewOtpResult.text.toString()
            if (otpText.isNotEmpty()) {
                val clipboard = requireContext().getSystemService(android.content.Context.CLIPBOARD_SERVICE) as android.content.ClipboardManager
                val clip = android.content.ClipData.newPlainText("OTP", otpText)
                clipboard.setPrimaryClip(clip)
                Toast.makeText(requireContext(), "OTP скопирован", Toast.LENGTH_SHORT).show()
            }
        }

        buttonGenerateOtp.setOnClickListener {
            val challenge = editTextChallenge.text.toString().trim()
            if (challenge.isEmpty()) {
                Toast.makeText(requireContext(), "Введите challenge", Toast.LENGTH_SHORT).show()
                return@setOnClickListener
            }
            showBiometricPrompt()
        }

        buttonConfirmLogin.setOnClickListener {
            val prefs = (requireActivity() as MainActivity).securePrefs
            val currentLoginCount = prefs.getInt("login_count", 0)
            prefs.edit {
                putInt("login_count", currentLoginCount + 1)
            }
            resetToInitialState()
            Toast.makeText(requireContext(), "Вход подтверждён", Toast.LENGTH_SHORT).show()
        }

        buttonCancelLogin.setOnClickListener {
            resetToInitialState()
            Toast.makeText(requireContext(), "Вход отменён", Toast.LENGTH_SHORT).show()
        }

        buttonReset.setOnClickListener {
            showResetConfirmationDialog()
        }
    }

    private fun startOtpGeneration() {
        val challenge = editTextChallenge.text.toString().trim()
        if (challenge.isEmpty()) {
            Toast.makeText(requireContext(), "Введите challenge", Toast.LENGTH_SHORT).show()
            return
        }

        progressBarOtp.visibility = View.VISIBLE
        buttonGenerateOtp.isEnabled = false

        val prefs = (requireActivity() as MainActivity).securePrefs
        val userKey = prefs.getString("user_key", null)
        val loginCount = prefs.getInt("login_count", 0)
        val failedAttempts = prefs.getInt("failed_attempts", 0)
        val lastFaultAt = prefs.getLong("last_fault_at", 0L)

        if (userKey == null) {
            progressBarOtp.visibility = View.GONE
            buttonGenerateOtp.isEnabled = true
            Toast.makeText(requireContext(), "Ошибка: ключ пользователя не найден", Toast.LENGTH_SHORT).show()
            return
        }

        // TODO: реализовать проверку бана по failedAttempts и lastFaultAt

        Log.d("MainOtp", "userKey (first 10): ${userKey.take(10)}")
        Log.d("MainOtp", "challenge: $challenge")

        val decrypted = OtpCrypto.decryptChallenge(challenge, userKey)
        if (decrypted == null) {
            val newFaults = failedAttempts + 1
            prefs.edit {
                putInt("failed_attempts", newFaults)
                putLong("last_fault_at", System.currentTimeMillis() / 1000)
            }
            progressBarOtp.visibility = View.GONE
            buttonGenerateOtp.isEnabled = true
            Toast.makeText(requireContext(), "Неверный challenge", Toast.LENGTH_SHORT).show()
            return
        }

        val (challengeRandom, timestampSec) = decrypted
        val currentTimeSec = System.currentTimeMillis() / 1000
        val timeoutSec = Config.CHALLENGE_TIMEOUT_MINUTES * 60

        if (currentTimeSec - timestampSec > timeoutSec) {
            val newFaults = failedAttempts + 1
            prefs.edit {
                putInt("failed_attempts", newFaults)
                putLong("last_fault_at", System.currentTimeMillis() / 1000)
            }
            progressBarOtp.visibility = View.GONE
            buttonGenerateOtp.isEnabled = true
            Toast.makeText(requireContext(), "Challenge истёк", Toast.LENGTH_SHORT).show()
            return
        }

        prefs.edit {
            putInt("failed_attempts", 0)
            remove("last_fault_at")
        }

        val plainOtp = "$challengeRandom:$loginCount"
        val otp = OtpCrypto.encryptOtp(plainOtp, userKey)

        textViewOtpResult.text = otp
        textViewOtpResult.visibility = View.VISIBLE
        buttonCopyOtp.visibility = View.VISIBLE
        actionButtonsLayout.visibility = View.VISIBLE
        buttonGenerateOtp.visibility = View.GONE
        progressBarOtp.visibility = View.GONE
    }

    private fun resetToInitialState() {
        textViewOtpResult.text = ""
        textViewOtpResult.visibility = View.GONE
        buttonCopyOtp.visibility = View.GONE
        actionButtonsLayout.visibility = View.GONE
        buttonGenerateOtp.visibility = View.VISIBLE
        buttonGenerateOtp.isEnabled = true
        progressBarOtp.visibility = View.GONE
        editTextChallenge.setText("")
    }

    private fun runOnUiThread(action: () -> Unit) {
        if (isAdded) {
            requireActivity().runOnUiThread(action)
        }
    }

    private fun setupBiometricPrompt() {
        executor = ContextCompat.getMainExecutor(requireContext())
        biometricPrompt = BiometricPrompt(this, executor,
            object : BiometricPrompt.AuthenticationCallback() {
                override fun onAuthenticationSucceeded(result: BiometricPrompt.AuthenticationResult) {
                    super.onAuthenticationSucceeded(result)
                    startOtpGeneration()
                }

                override fun onAuthenticationError(errorCode: Int, errString: CharSequence) {
                    super.onAuthenticationError(errorCode, errString)
                    runOnUiThread {
                        Toast.makeText(requireContext(), "Ошибка биометрии: $errString", Toast.LENGTH_SHORT).show()
                    }
                }

                override fun onAuthenticationFailed() {
                    super.onAuthenticationFailed()
                    runOnUiThread {
                        Toast.makeText(requireContext(), "Отпечаток не распознан", Toast.LENGTH_SHORT).show()
                    }
                }
            })

        promptInfo = BiometricPrompt.PromptInfo.Builder()
            .setTitle("Подтверждение личности")
            .setSubtitle("Требуется отпечаток пальца для генерации OTP")
            .setNegativeButtonText("Отмена")
            .build()
    }

    private fun showResetConfirmationDialog() {
        AlertDialog.Builder(requireContext())
            .setTitle(R.string.reset_confirm_title)
            .setMessage(R.string.reset_confirm_message)
            .setPositiveButton(R.string.reset_confirm_positive) { _, _ ->
                (requireActivity() as MainActivity).resetTokenData()
            }
            .setNegativeButton(R.string.reset_confirm_negative, null)
            .show()
    }

    private fun showBiometricPrompt() {
        biometricPrompt.authenticate(promptInfo)
    }
}