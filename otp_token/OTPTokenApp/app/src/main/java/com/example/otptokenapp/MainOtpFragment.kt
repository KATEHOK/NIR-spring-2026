package com.example.otptokenapp

import android.os.Bundle
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.TextView
import androidx.fragment.app.Fragment

class MainOtpFragment : Fragment() {
    override fun onCreateView(
        inflater: LayoutInflater, container: ViewGroup?, savedInstanceState: Bundle?
    ): View {
        val textView = TextView(requireContext())
        textView.text = "Основной экран OTP (будет реализован позже)"
        textView.textSize = 20f
        textView.gravity = android.view.Gravity.CENTER
        return textView
    }
}