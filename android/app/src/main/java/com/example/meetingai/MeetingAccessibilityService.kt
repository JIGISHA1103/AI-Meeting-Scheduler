package com.example.meetingai

import android.accessibilityservice.AccessibilityService
import android.util.Log
import android.view.accessibility.AccessibilityEvent
import android.view.accessibility.AccessibilityNodeInfo

class MeetingAccessibilityService : AccessibilityService() {

    companion object {
        private const val TAG = "MeetingAccessibility"
    }

    override fun onServiceConnected() {
        super.onServiceConnected()

        Log.d(
            TAG,
            "Accessibility Service connected"
        )
    }

    override fun onAccessibilityEvent(
        event: AccessibilityEvent?
    ) {

        if (event == null) {
            return
        }

        val rootNode = rootInActiveWindow

        if (rootNode == null) {
            return
        }

        val screenText = StringBuilder()

        collectText(
            rootNode,
            screenText
        )

        val text = screenText
            .toString()
            .trim()

        if (text.isNotEmpty()) {

            Log.d(
                TAG,
                "Screen text:\n$text"
            )
        }
    }

    private fun collectText(
        node: AccessibilityNodeInfo?,
        textBuilder: StringBuilder
    ) {

        if (node == null) {
            return
        }

        val text = node.text

        if (!text.isNullOrBlank()) {

            textBuilder.append(text)
            textBuilder.append(" ")
        }

        val contentDescription =
            node.contentDescription

        if (!contentDescription.isNullOrBlank()) {

            textBuilder.append(contentDescription)
            textBuilder.append(" ")
        }

        for (i in 0 until node.childCount) {

            collectText(
                node.getChild(i),
                textBuilder
            )
        }
    }

    override fun onInterrupt() {

        Log.d(
            TAG,
            "Accessibility Service interrupted"
        )
    }
}