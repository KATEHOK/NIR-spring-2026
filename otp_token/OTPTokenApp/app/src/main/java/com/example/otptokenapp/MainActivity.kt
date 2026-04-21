package com.example.otptokenapp

import android.app.AlertDialog
import android.os.Bundle
import android.view.View
import android.widget.FrameLayout
import android.widget.ProgressBar
import android.widget.TextView
import androidx.appcompat.app.AppCompatActivity
import androidx.biometric.BiometricManager
import androidx.biometric.BiometricPrompt
import androidx.core.content.ContextCompat
import java.util.concurrent.Executor
import androidx.lifecycle.ViewModelProvider

class MainActivity : AppCompatActivity() {

    private lateinit var textViewStatus: TextView
    private lateinit var progressBar: ProgressBar
    private lateinit var executor: Executor
    private lateinit var biometricPrompt: BiometricPrompt
    private lateinit var promptInfo: BiometricPrompt.PromptInfo
    private lateinit var viewModel: MainViewModel
    private lateinit var fragmentContainer: FrameLayout
    private lateinit var registrationViewModel: RegistrationViewModel

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)
        registrationViewModel = ViewModelProvider(this)[RegistrationViewModel::class.java]

        fragmentContainer = findViewById(R.id.fragmentContainer)
        textViewStatus = findViewById(R.id.textViewStatus)
        progressBar = findViewById(R.id.progressBar)

        viewModel = ViewModelProvider(this)[MainViewModel::class.java]

        if (viewModel.isAuthenticated) {
            showMainContent()
        } else {
            checkBiometricAvailability()
        }
    }

    private fun checkBiometricAvailability() {
        val biometricManager = BiometricManager.from(this)
        when (biometricManager.canAuthenticate(BiometricManager.Authenticators.BIOMETRIC_STRONG)) {
            BiometricManager.BIOMETRIC_SUCCESS -> {
                textViewStatus.text = getString(R.string.biometric_ready)
                setupBiometricPrompt()
                showBiometricPrompt()
            }
            BiometricManager.BIOMETRIC_ERROR_NO_HARDWARE -> {
                textViewStatus.text = "Устройство не поддерживает аутентификацию по биометрии"
                progressBar.visibility = ProgressBar.GONE
            }
            BiometricManager.BIOMETRIC_ERROR_HW_UNAVAILABLE -> {
                textViewStatus.text = "Биометрическое оборудование недоступно"
                progressBar.visibility = ProgressBar.GONE
            }
            BiometricManager.BIOMETRIC_ERROR_NONE_ENROLLED -> {
                textViewStatus.text = "Нет зарегистрированных отпечатков пальцев"
                progressBar.visibility = ProgressBar.GONE
            }
            else -> {
                textViewStatus.text = "Аутентификация по биометрии недоступна"
                progressBar.visibility = ProgressBar.GONE
            }
        }
    }

    private fun setupBiometricPrompt() {
        executor = ContextCompat.getMainExecutor(this)
        biometricPrompt = BiometricPrompt(this, executor,
            object : BiometricPrompt.AuthenticationCallback() {
                override fun onAuthenticationSucceeded(result: BiometricPrompt.AuthenticationResult) {
                    super.onAuthenticationSucceeded(result)
                    runOnUiThread {
                        viewModel.isAuthenticated = true
                        textViewStatus.text = "Личность успешно подтверждена!"
                        progressBar.visibility = ProgressBar.GONE
                        showMainContent()
                    }
                }

                override fun onAuthenticationError(errorCode: Int, errString: CharSequence) {
                    super.onAuthenticationError(errorCode, errString)
                    runOnUiThread {
                        if (errorCode == BiometricPrompt.ERROR_NEGATIVE_BUTTON) {
                            progressBar.visibility = ProgressBar.GONE
                            showRetryOrExitDialog()
                        } else {
                            textViewStatus.text = getString(R.string.error_biometric_format, errString)
                            progressBar.visibility = ProgressBar.GONE
                        }
                    }
                }

                override fun onAuthenticationFailed() {
                    super.onAuthenticationFailed()
                    runOnUiThread {
                        textViewStatus.text = getString(R.string.error_biometric_failed)
                    }
                }
            })

        promptInfo = BiometricPrompt.PromptInfo.Builder()
            .setTitle("Аутентификация")
            .setSubtitle("Подтвердите личность с помощью отпечатка пальца")
            .setDescription("Приложение OTP Token требует подтверждения")
            .setNegativeButtonText("Отмена")
            .build()
    }

    private fun showBiometricPrompt() {
        progressBar.visibility = ProgressBar.VISIBLE
        biometricPrompt.authenticate(promptInfo)
    }

    private fun showRetryOrExitDialog() {
        AlertDialog.Builder(this)
            .setTitle(getString(R.string.dialog_title))
            .setMessage(getString(R.string.dialog_message))
            .setPositiveButton(getString(R.string.dialog_retry)) { _, _ ->
                showBiometricPrompt()
            }
            .setNegativeButton(getString(R.string.dialog_exit)) { _, _ ->
                finishAffinity()
            }
            .setCancelable(false) // запрещаем закрытие по нажатию вне диалога
            .show()
    }

    fun showMainContent() {
        textViewStatus.visibility = View.GONE
        progressBar.visibility = View.GONE
        fragmentContainer.visibility = View.VISIBLE

        // Если уже зарегистрированы, показываем основной экран OTP
        val prefs = getSharedPreferences("secure_prefs", MODE_PRIVATE)
        if (prefs.getBoolean("is_registered", false)) {
            showMainOtpScreen()
            return
        }

        // Если ожидаем подтверждения (после нажатия "Далее") - показываем фрагмент подтверждения
        if (registrationViewModel.awaitingConfirmation) {
            supportFragmentManager.beginTransaction()
                .replace(R.id.fragmentContainer, RegisterConfirmFragment())
                .commitAllowingStateLoss()
        } else {
            supportFragmentManager.beginTransaction()
                .replace(R.id.fragmentContainer, RegisterInitFragment())
                .commitAllowingStateLoss()
        }
    }

    fun showMainOtpScreen() {
        // Временно: показываем сообщение, позже заменим на фрагмент OTP
        val fragment = supportFragmentManager.findFragmentById(R.id.fragmentContainer)
        if (fragment !is MainOtpFragment) {
            supportFragmentManager.beginTransaction()
                .replace(R.id.fragmentContainer, MainOtpFragment())
                .commitAllowingStateLoss()
        }
    }
}