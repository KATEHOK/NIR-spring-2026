package com.example.otptokenapp

import android.content.Context
import android.os.Build
import android.security.keystore.KeyGenParameterSpec
import android.security.keystore.KeyProperties
import android.util.Log
import androidx.core.content.edit
import java.security.KeyStore
import javax.crypto.Cipher
import javax.crypto.KeyGenerator
import javax.crypto.SecretKey
import javax.crypto.spec.GCMParameterSpec

object CryptoHelper {
    private const val MASTER_KEY_ALIAS = "otp_master_key"
    private const val ANDROID_KEYSTORE = "AndroidKeyStore"

    fun getMasterKey(context: Context): SecretKey {
        Log.d("CryptoHelper", "getMasterKey started")
        // Проверяем, существует ли уже ключ
        val keyStore = KeyStore.getInstance(ANDROID_KEYSTORE)
        keyStore.load(null)
        keyStore.getKey(MASTER_KEY_ALIAS, null)?.let {
            return it as SecretKey
        }

        // Если не существует – создаём новый
        val builder = KeyGenParameterSpec.Builder(
            MASTER_KEY_ALIAS,
            KeyProperties.PURPOSE_ENCRYPT or KeyProperties.PURPOSE_DECRYPT
        )
            .setBlockModes(KeyProperties.BLOCK_MODE_GCM)
            .setEncryptionPaddings(KeyProperties.ENCRYPTION_PADDING_NONE)
            .setUserAuthenticationRequired(true)

        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.R) {
            builder.setUserAuthenticationParameters(0, KeyProperties.AUTH_BIOMETRIC_STRONG)
        } else {
            @Suppress("DEPRECATION")
            builder.setUserAuthenticationValidityDurationSeconds(-1)
        }

        val keyGenParameterSpec = builder.build()
        val keyGenerator = KeyGenerator.getInstance(
            KeyProperties.KEY_ALGORITHM_AES,
            ANDROID_KEYSTORE
        )
        keyGenerator.init(keyGenParameterSpec)
        return keyGenerator.generateKey()
    }

    fun encryptData(data: ByteArray, secretKey: SecretKey): ByteArray {
        Log.d("CryptoHelper", "encryptData started")
        val cipher = Cipher.getInstance("AES/GCM/NoPadding")
        cipher.init(Cipher.ENCRYPT_MODE, secretKey)
        val iv = cipher.iv
        val ciphertext = cipher.doFinal(data)
        return iv + ciphertext
    }

    fun decryptData(encrypted: ByteArray, secretKey: SecretKey): ByteArray {
        val iv = encrypted.copyOfRange(0, 12)
        val ciphertext = encrypted.copyOfRange(12, encrypted.size)
        val cipher = Cipher.getInstance("AES/GCM/NoPadding")
        val spec = GCMParameterSpec(128, iv)
        cipher.init(Cipher.DECRYPT_MODE, secretKey, spec)
        return cipher.doFinal(ciphertext)
    }

    // Сохранение строки (зашифрованной)
    fun saveEncryptedString(context: Context, key: String, value: String, secretKey: SecretKey) {
        val encrypted = encryptData(value.toByteArray(), secretKey)
        val prefs = context.getSharedPreferences("secure_prefs", Context.MODE_PRIVATE)
        prefs.edit {
            putString(key, android.util.Base64.encodeToString(encrypted, android.util.Base64.DEFAULT))
        }
    }

    // Получение строки (расшифрованной)
    fun getEncryptedString(context: Context, key: String, secretKey: SecretKey): String? {
        Log.d("CryptoHelper", "getEncryptedString started")
        val prefs = context.getSharedPreferences("secure_prefs", Context.MODE_PRIVATE)
        val base64 = prefs.getString(key, null) ?: return null
        val encrypted = android.util.Base64.decode(base64, android.util.Base64.DEFAULT)
        val decrypted = decryptData(encrypted, secretKey)
        return String(decrypted)
    }

    // Сохранение произвольных байтов (зашифрованных)
    fun saveEncryptedBytes(context: Context, key: String, data: ByteArray, secretKey: SecretKey) {
        Log.d("CryptoHelper", "saveEncryptedBytes started")
        val encrypted = encryptData(data, secretKey)
        val prefs = context.getSharedPreferences("secure_prefs", Context.MODE_PRIVATE)
        prefs.edit {
            putString(key, android.util.Base64.encodeToString(encrypted, android.util.Base64.DEFAULT))
        }
    }

    // Получение произвольных байтов (расшифрованных)
    fun getEncryptedBytes(context: Context, key: String, secretKey: SecretKey): ByteArray? {
        val prefs = context.getSharedPreferences("secure_prefs", Context.MODE_PRIVATE)
        val base64 = prefs.getString(key, null) ?: return null
        val encrypted = android.util.Base64.decode(base64, android.util.Base64.DEFAULT)
        return decryptData(encrypted, secretKey)
    }

    fun deleteMasterKey() {
        try {
            val keyStore = KeyStore.getInstance(ANDROID_KEYSTORE)
            keyStore.load(null)
            if (keyStore.containsAlias(MASTER_KEY_ALIAS)) {
                keyStore.deleteEntry(MASTER_KEY_ALIAS)
            }
        } catch (e: Exception) {
            Log.e("CryptoHelper", "Failed to delete master key", e)
        }
    }
}