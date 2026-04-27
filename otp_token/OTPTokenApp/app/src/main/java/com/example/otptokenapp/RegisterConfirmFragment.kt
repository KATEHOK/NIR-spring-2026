package com.example.otptokenapp

import android.os.Bundle
import android.text.Editable
import android.text.TextWatcher
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.Button
import android.widget.EditText
import android.widget.Toast
import androidx.core.content.edit
import androidx.fragment.app.Fragment
import androidx.lifecycle.ViewModelProvider

class RegisterConfirmFragment : Fragment() {

    private lateinit var editTextKeyPart: EditText
    private lateinit var buttonConfirm: Button
    private lateinit var registrationViewModel: RegistrationViewModel

    override fun onCreateView(
        inflater: LayoutInflater, container: ViewGroup?, savedInstanceState: Bundle?
    ): View? {
        return inflater.inflate(
            R.layout.fragment_register_confirm,
            container,
            false
        )
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

        buttonConfirm.setOnClickListener {
            val keyPart = editTextKeyPart.text.toString().trim()
            if (keyPart.isEmpty()) {
                Toast.makeText(
                    requireContext(),
                    "Введите key_part",
                    Toast.LENGTH_SHORT
                ).show()
                return@setOnClickListener
            }
            val pinCode = registrationViewModel.generatedPinCode
            if (pinCode == null) {
                Toast.makeText(
                    requireContext(),
                    "Ошибка: PIN-код не найден",
                    Toast.LENGTH_SHORT
                ).show()
                return@setOnClickListener
            }
            val userKey = "$keyPart:$pinCode"

            val prefs = (requireActivity() as MainActivity).securePrefs
            prefs.edit {
                putString("user_key", userKey)
                putInt("login_count", 0)
                putBoolean("is_registered", true)
            }

            Toast.makeText(
                requireContext(),
                R.string.saving_success,
                Toast.LENGTH_LONG
            ).show()
            (requireActivity() as MainActivity).showMainOtpScreen()
        }
    }
}