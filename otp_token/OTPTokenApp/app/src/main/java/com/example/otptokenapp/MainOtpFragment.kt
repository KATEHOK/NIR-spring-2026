package com.example.otptokenapp

import android.app.AlertDialog
import android.os.Bundle
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.Button
import android.widget.EditText
import android.widget.TextView
import android.widget.Toast
import androidx.fragment.app.Fragment

class MainOtpFragment : Fragment() {

    private lateinit var editTextChallenge: EditText
    private lateinit var buttonGenerateOtp: Button
    private lateinit var textViewOtpResult: TextView
    private lateinit var buttonReset: Button

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

        buttonGenerateOtp.setOnClickListener {
            Toast.makeText(
                requireContext(),
                "Генерация OTP будет реализована позже",
                Toast.LENGTH_SHORT
            ).show()
        }

        buttonReset.setOnClickListener {
            showResetConfirmationDialog()
        }
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
}