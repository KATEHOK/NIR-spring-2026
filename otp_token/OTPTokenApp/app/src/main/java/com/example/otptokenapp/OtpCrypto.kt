package com.example.otptokenapp

import android.util.Base64
import android.util.Log
import java.security.MessageDigest
import javax.crypto.Cipher
import javax.crypto.spec.GCMParameterSpec
import javax.crypto.spec.SecretKeySpec

object OtpCrypto {
    private const val TAG = "OtpCrypto"
    private const val AES_MODE = "AES/GCM/NoPadding"
    private const val TAG_LENGTH_BITS = 128

    private fun deriveKey(userKey: String): SecretKeySpec {
        val keyBytes = userKey.toByteArray(Charsets.UTF_8)
        val sha = MessageDigest.getInstance("SHA-256")
        val derivedKey = sha.digest(keyBytes)
        return SecretKeySpec(derivedKey, "AES")
    }

    fun decryptChallenge(encryptedChallengeBase64: String, userKey: String): Pair<String, Long>? {
        return try {
            Log.d(TAG, "decryptChallenge: encryptedChallengeBase64 = $encryptedChallengeBase64")
            val encrypted = Base64.decode(encryptedChallengeBase64, Base64.DEFAULT)
            Log.d(TAG, "decryptChallenge: encrypted size = ${encrypted.size}")
            val key = deriveKey(userKey)
            val cipher = Cipher.getInstance(AES_MODE)
            val iv = encrypted.copyOfRange(0, 12)
            val ciphertext = encrypted.copyOfRange(12, encrypted.size)
            Log.d(TAG, "decryptChallenge: iv size = ${iv.size}, ciphertext size = ${ciphertext.size}")
            val spec = GCMParameterSpec(TAG_LENGTH_BITS, iv)
            cipher.init(Cipher.DECRYPT_MODE, key, spec)
            val decrypted = cipher.doFinal(ciphertext)
            val parts = String(decrypted).split(":")
            if (parts.size != 2) null else parts[0] to parts[1].toLong()
        } catch (e: Exception) {
            Log.e(TAG, "decryptChallenge failed", e)
            null
        }
    }

    fun encryptOtp(plainOtp: String, userKey: String): String {
        val data = plainOtp.toByteArray(Charsets.UTF_8)
        val key = deriveKey(userKey)
        val cipher = Cipher.getInstance(AES_MODE)
        cipher.init(Cipher.ENCRYPT_MODE, key)
        val iv = cipher.iv
        val ciphertext = cipher.doFinal(data)
        val combined = iv + ciphertext
        return Base64.encodeToString(combined, Base64.DEFAULT)
    }
}