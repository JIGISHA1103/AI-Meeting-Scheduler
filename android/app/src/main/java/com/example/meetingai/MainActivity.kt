
package com.example.meetingai

import android.Manifest
import android.content.Intent
import android.content.pm.PackageManager
import android.os.Bundle
import android.speech.RecognitionListener
import android.speech.RecognizerIntent
import android.speech.SpeechRecognizer
import android.util.Log

import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size

import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.foundation.verticalScroll

import androidx.compose.material3.Button
import androidx.compose.material3.IconButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton

import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue

import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.tooling.preview.Preview
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp

import com.example.meetingai.ui.theme.MeetingAITheme

import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext

import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody

import org.json.JSONObject

import java.util.Locale
import java.util.concurrent.TimeUnit


// ==================================================
// Backend Configuration
// ==================================================

private const val BASE_URL =
    "http://192.168.0.165:8000"

private const val TAG =
    "MeetingAI"


// ==================================================
// OkHttp Client
// ==================================================

private val client = OkHttpClient.Builder()

    .connectTimeout(
        30,
        TimeUnit.SECONDS
    )

    .readTimeout(
        120,
        TimeUnit.SECONDS
    )

    .writeTimeout(
        30,
        TimeUnit.SECONDS
    )

    .build()


// ==================================================
// Format FastAPI Scheduling Response
// ==================================================

private fun formatScheduleResult(
    responseBody: String
): String {

    return try {

        val json =
            JSONObject(responseBody)

        val status =
            json.optString("status")


        // --------------------------------------------------
        // Successful scheduling
        // --------------------------------------------------

        if (status == "success") {

            val meeting =
                json.optJSONObject("meeting")

            val title =
                meeting?.optString(
                    "title",
                    "Meeting"
                ) ?: "Meeting"

            val date =
                meeting?.optString(
                    "date",
                    ""
                ) ?: ""

            val time =
                meeting?.optString(
                    "time",
                    ""
                ) ?: ""

            val duration =
                meeting?.optInt(
                    "duration",
                    60
                ) ?: 60

            val participants =
                meeting?.optJSONArray(
                    "participants"
                )


            val participantText =
                if (
                    participants != null &&
                    participants.length() > 0
                ) {

                    buildString {

                        for (
                        i in 0 until participants.length()
                        ) {

                            append(
                                participants.optString(i)
                            )

                            if (
                                i < participants.length() - 1
                            ) {

                                append(", ")
                            }
                        }
                    }

                } else {

                    "None"
                }


            buildString {

                append(
                    "Meeting Scheduled Successfully\n\n"
                )

                append("Meeting: ")
                append(title)
                append("\n")

                append("Date: ")
                append(date)
                append("\n")

                append("Time: ")
                append(time)
                append("\n")

                append("Duration: ")
                append(duration)
                append(" minutes\n\n")

                append("Participant: ")
                append(participantText)
            }


            // --------------------------------------------------
            // Scheduling conflict
            // --------------------------------------------------

        } else if (status == "conflict") {

            val message =
                json.optString(
                    "message",
                    "The requested time is already occupied."
                )

            "Scheduling Conflict\n\n$message"


            // --------------------------------------------------
            // Scheduling error
            // --------------------------------------------------

        } else if (status == "error") {

            val message =
                json.optString(
                    "message",
                    "Something went wrong while scheduling the meeting."
                )

            "Scheduling Error\n\n$message"


            // --------------------------------------------------
            // Unknown response
            // --------------------------------------------------

        } else {

            responseBody
        }

    } catch (e: Exception) {

        Log.e(
            TAG,
            "Failed to format scheduling response",
            e
        )

        responseBody
    }
}


// ==================================================
// Poll Schedule Status
// ==================================================

private suspend fun pollScheduleStatus(
    requestId: String
): String {

    // --------------------------------------------------
    // Maximum number of status checks
    // --------------------------------------------------

    val maxAttempts =
        30


    repeat(maxAttempts) { attempt ->

        Log.d(
            TAG,
            "Checking schedule status: attempt ${attempt + 1}/$maxAttempts"
        )


        // --------------------------------------------------
        // Create GET request
        // --------------------------------------------------

        val request =
            Request.Builder()

                .url(
                    "$BASE_URL/schedule/status/$requestId"
                )

                .get()

                .addHeader(
                    "Accept",
                    "application/json"
                )

                .build()


        // --------------------------------------------------
        // Execute request
        // --------------------------------------------------

        val response =
            client
                .newCall(request)
                .execute()


        val responseBody =
            response.body?.string()
                ?: ""


        Log.d(
            TAG,
            "Status response code: ${response.code}"
        )

        Log.d(
            TAG,
            "Status response: $responseBody"
        )


        // --------------------------------------------------
        // HTTP error
        // --------------------------------------------------

        if (!response.isSuccessful) {

            return "Server error ${response.code}: $responseBody"
        }


        // --------------------------------------------------
        // Parse status response
        // --------------------------------------------------

        val json =
            JSONObject(responseBody)

        val status =
            json.optString("status")


        Log.d(
            TAG,
            "Current scheduling status: $status"
        )


        // --------------------------------------------------
        // Handle current status
        // --------------------------------------------------

        when (status) {


            // --------------------------------------------------
            // Still processing
            // --------------------------------------------------

            "processing" -> {

                withContext(
                    Dispatchers.Main
                ) {

                    // UI is updated from the caller
                    // when polling starts.
                }


                // Wait 2 seconds before checking again

                delay(2000)
            }


            // --------------------------------------------------
            // Successfully completed
            // --------------------------------------------------

            "success" -> {

                // The current status endpoint only returns
                // request status information.
                //
                // Therefore, display a successful completion
                // message here.

                return "Meeting Scheduled Successfully"
            }


            // --------------------------------------------------
            // Scheduling conflict
            // --------------------------------------------------

            "conflict" -> {

                val message =
                    json.optString(
                        "error_message",
                        "The requested time is already occupied."
                    )

                return "Scheduling Conflict\n\n$message"
            }


            // --------------------------------------------------
            // Error
            // --------------------------------------------------

            "error" -> {

                val message =
                    json.optString(
                        "error_message",
                        "Something went wrong while scheduling the meeting."
                    )

                return "Scheduling Error\n\n$message"
            }


            // --------------------------------------------------
            // Request not found
            // --------------------------------------------------

            "not_found" -> {

                return "Scheduling Error\n\nRequest ID was not found."
            }


            // --------------------------------------------------
            // Unknown status
            // --------------------------------------------------

            else -> {

                return "Unknown scheduling status: $status"
            }
        }
    }


    // --------------------------------------------------
    // Maximum polling time reached
    // --------------------------------------------------

    return "Scheduling timed out. Please check your calendar."
}


// ==================================================
// Main Activity
// ==================================================

class MainActivity : ComponentActivity() {

    override fun onCreate(
        savedInstanceState: Bundle?
    ) {

        super.onCreate(
            savedInstanceState
        )


        enableEdgeToEdge()


        setContent {

            MeetingAITheme {

                MeetingAIScreen()
            }
        }
    }
}


// ==================================================
// Main UI + Speech-to-Text
// ==================================================

@Composable
fun MeetingAIScreen() {

    val context =
        LocalContext.current


    // ==================================================
    // Meeting Request Text
    // ==================================================

    var meetingText by remember {

        mutableStateOf("")
    }


    // ==================================================
    // Scheduling Result
    // ==================================================

    var resultText by remember {

        mutableStateOf("")
    }


    // ==================================================
    // Loading State
    // ==================================================

    var isLoading by remember {

        mutableStateOf(false)
    }


    // ==================================================
    // Speech Recognition State
    // ==================================================

    var isListening by remember {

        mutableStateOf(false)
    }


    // ==================================================
    // Create SpeechRecognizer
    // ==================================================

    val speechRecognizer =
        remember {

            if (
                SpeechRecognizer
                    .isRecognitionAvailable(context)
            ) {

                SpeechRecognizer
                    .createSpeechRecognizer(context)

            } else {

                null
            }
        }


    // ==================================================
    // Speech Recognition Listener
    // ==================================================

    DisposableEffect(
        speechRecognizer
    ) {

        if (
            speechRecognizer != null
        ) {

            speechRecognizer.setRecognitionListener(

                object : RecognitionListener {


                    override fun onReadyForSpeech(
                        params: Bundle?
                    ) {

                        isListening =
                            true

                        Log.d(
                            TAG,
                            "Speech recognition ready"
                        )
                    }


                    override fun onBeginningOfSpeech() {

                        isListening =
                            true

                        Log.d(
                            TAG,
                            "Speech started"
                        )
                    }


                    override fun onRmsChanged(
                        rmsdB: Float
                    ) {
                        // Not required
                    }


                    override fun onBufferReceived(
                        buffer: ByteArray?
                    ) {
                        // Not required
                    }


                    override fun onEndOfSpeech() {

                        isListening =
                            false

                        Log.d(
                            TAG,
                            "Speech ended"
                        )
                    }


                    override fun onError(
                        error: Int
                    ) {

                        isListening =
                            false

                        Log.e(
                            TAG,
                            "Speech recognition error: $error"
                        )
                    }


                    override fun onResults(
                        results: Bundle?
                    ) {

                        isListening =
                            false


                        val matches =
                            results?.getStringArrayList(
                                SpeechRecognizer.RESULTS_RECOGNITION
                            )


                        if (
                            !matches.isNullOrEmpty()
                        ) {

                            meetingText =
                                matches[0]

                            Log.d(
                                TAG,
                                "Recognized speech: ${matches[0]}"
                            )
                        }
                    }


                    override fun onPartialResults(
                        partialResults: Bundle?
                    ) {
                        // Not required
                    }


                    override fun onEvent(
                        eventType: Int,
                        params: Bundle?
                    ) {
                        // Not required
                    }
                }
            )
        }


        // --------------------------------------------------
        // Cleanup SpeechRecognizer
        // --------------------------------------------------

        onDispose {

            speechRecognizer?.destroy()
        }
    }


    // ==================================================
    // Microphone Permission Launcher
    // ==================================================

    val microphonePermissionLauncher =
        rememberLauncherForActivityResult(

            ActivityResultContracts
                .RequestPermission()

        ) { granted ->

            if (granted) {

                startListening(
                    speechRecognizer =
                    speechRecognizer,

                    context =
                    context
                )

            } else {

                resultText =
                    "Microphone permission is required for voice input."
            }
        }


    // ==================================================
    // Scroll State
    // ==================================================

    val scrollState =
        rememberScrollState()


    // ==================================================
    // UI
    // ==================================================

    Scaffold(

        modifier =
        Modifier.fillMaxSize()

    ) { innerPadding ->


        Column(

            modifier =
            Modifier

                .fillMaxSize()

                .padding(
                    innerPadding
                )

                .padding(
                    24.dp
                )

                .verticalScroll(
                    scrollState
                ),


            horizontalAlignment =
            Alignment.CenterHorizontally,


            verticalArrangement =
            Arrangement.Center

        ) {


            // ==================================================
            // Title
            // ==================================================

            Text(

                text =
                "Meeting AI",

                fontSize =
                32.sp
            )


            Spacer(
                modifier =
                Modifier.height(8.dp)
            )


            Text(

                text =
                "Schedule a Meeting",

                fontSize =
                20.sp
            )


            Spacer(
                modifier =
                Modifier.height(24.dp)
            )


            // ==================================================
            // Meeting Request Input
            // ==================================================

            OutlinedTextField(

                value =
                meetingText,


                onValueChange = {

                    meetingText =
                        it
                },


                modifier =
                Modifier.fillMaxWidth(),


                label = {

                    Text(
                        "Meeting request"
                    )
                },


                placeholder = {

                    Text(
                        "Example: Schedule a project meeting tomorrow at 3 PM"
                    )
                },


                minLines =
                4,


                keyboardOptions =
                KeyboardOptions(

                    keyboardType =
                    KeyboardType.Text
                )
            )


            Spacer(
                modifier =
                Modifier.height(16.dp)
            )


            // ==================================================
            // Microphone + Clear Buttons
            // ==================================================

            Row(

                modifier =
                Modifier.fillMaxWidth(),


                horizontalArrangement =
                Arrangement.Center,


                verticalAlignment =
                Alignment.CenterVertically

            ) {


                // --------------------------------------------------
                // Microphone Button
                // --------------------------------------------------

                IconButton(

                    onClick = {

                        if (isListening) {

                            speechRecognizer
                                ?.stopListening()

                            isListening =
                                false

                        } else {


                            if (

                                context
                                    .checkSelfPermission(
                                        Manifest.permission.RECORD_AUDIO
                                    ) ==
                                PackageManager.PERMISSION_GRANTED

                            ) {

                                startListening(

                                    speechRecognizer =
                                    speechRecognizer,

                                    context =
                                    context
                                )

                            } else {

                                microphonePermissionLauncher
                                    .launch(
                                        Manifest.permission.RECORD_AUDIO
                                    )
                            }
                        }
                    },


                    modifier =
                    Modifier.size(64.dp),


                    enabled =
                    !isLoading

                ) {


                    Text(

                        text =
                        if (isListening) {

                            "■"

                        } else {

                            "🎤"
                        },


                        fontSize =
                        32.sp
                    )
                }


                // --------------------------------------------------
                // Clear Button
                // --------------------------------------------------

                TextButton(

                    onClick = {

                        meetingText =
                            ""

                        resultText =
                            ""
                    },


                    enabled =
                    !isLoading

                ) {

                    Text(
                        text =
                        "Clear"
                    )
                }
            }


            // ==================================================
            // Listening Status
            // ==================================================

            Text(

                text =
                if (isListening) {

                    "Listening..."

                } else {

                    "Tap microphone to speak"
                }
            )


            Spacer(
                modifier =
                Modifier.height(24.dp)
            )


            // ==================================================
            // Schedule Meeting Button
            // ==================================================

            Button(

                onClick = {


                    // --------------------------------------------------
                    // Validate input
                    // --------------------------------------------------

                    if (
                        meetingText.isBlank()
                    ) {

                        resultText =
                            "Please enter a meeting request."

                        return@Button
                    }


                    // --------------------------------------------------
                    // Start loading
                    // --------------------------------------------------

                    isLoading =
                        true


                    resultText =
                        "Sending request..."


                    // --------------------------------------------------
                    // Background coroutine
                    // --------------------------------------------------

                    CoroutineScope(
                        Dispatchers.IO
                    ).launch {


                        try {


                            Log.d(
                                TAG,
                                "Sending request to FastAPI: $BASE_URL/schedule"
                            )


                            Log.d(
                                TAG,
                                "Meeting request: $meetingText"
                            )


                            // ==================================================
                            // Create JSON
                            // ==================================================

                            val json =
                                JSONObject()


                            json.put(
                                "text",
                                meetingText
                            )


                            val mediaType =
                                "application/json"
                                    .toMediaType()


                            val requestBody =
                                json
                                    .toString()
                                    .toRequestBody(
                                        mediaType
                                    )


                            // ==================================================
                            // POST /schedule
                            // ==================================================

                            val request =
                                Request.Builder()

                                    .url(
                                        "$BASE_URL/schedule"
                                    )

                                    .post(
                                        requestBody
                                    )

                                    .addHeader(
                                        "Content-Type",
                                        "application/json"
                                    )

                                    .build()


                            val response =
                                client
                                    .newCall(request)
                                    .execute()


                            val responseBody =
                                response.body
                                    ?.string()
                                    ?: ""


                            Log.d(
                                TAG,
                                "FastAPI response code: ${response.code}"
                            )


                            Log.d(
                                TAG,
                                "FastAPI response: $responseBody"
                            )


                            // ==================================================
                            // Handle HTTP error
                            // ==================================================

                            if (
                                !response.isSuccessful
                            ) {

                                withContext(
                                    Dispatchers.Main
                                ) {

                                    isLoading =
                                        false

                                    resultText =
                                        "Server error ${response.code}: $responseBody"
                                }

                                return@launch
                            }


                            // ==================================================
                            // Parse /schedule response
                            // ==================================================

                            val scheduleJson =
                                JSONObject(
                                    responseBody
                                )


                            val requestId =
                                scheduleJson.optString(
                                    "request_id"
                                )


                            val initialStatus =
                                scheduleJson.optString(
                                    "status"
                                )


                            Log.d(
                                TAG,
                                "Request ID: $requestId"
                            )


                            Log.d(
                                TAG,
                                "Initial status: $initialStatus"
                            )


                            // ==================================================
                            // Validate request ID
                            // ==================================================

                            if (
                                requestId.isBlank()
                            ) {

                                withContext(
                                    Dispatchers.Main
                                ) {

                                    isLoading =
                                        false

                                    resultText =
                                        "Scheduling failed: no request ID returned."
                                }

                                return@launch
                            }


                            // ==================================================
                            // Show processing message
                            // ==================================================

                            withContext(
                                Dispatchers.Main
                            ) {

                                resultText =
                                    "Request received.\n\nProcessing meeting..."
                            }


                            // ==================================================
                            // Poll backend
                            // ==================================================

                            val finalResult =
                                pollScheduleStatus(
                                    requestId
                                )


                            // ==================================================
                            // Show final result
                            // ==================================================

                            withContext(
                                Dispatchers.Main
                            ) {

                                isLoading =
                                    false

                                resultText =
                                    finalResult
                            }


                        } catch (e: Exception) {


                            // ==================================================
                            // Handle connection / runtime errors
                            // ==================================================

                            Log.e(
                                TAG,
                                "FastAPI scheduling request failed",
                                e
                            )


                            withContext(
                                Dispatchers.Main
                            ) {

                                isLoading =
                                    false

                                resultText =
                                    "Connection error: ${e.message}"
                            }
                        }
                    }
                },


                modifier =
                Modifier.fillMaxWidth(),


                enabled =
                !isLoading

            ) {


                Text(

                    text =
                    if (isLoading) {

                        "Scheduling..."

                    } else {

                        "Schedule Meeting"
                    }
                )
            }


            Spacer(
                modifier =
                Modifier.height(24.dp)
            )


            // ==================================================
            // Result
            // ==================================================

            Text(
                text =
                "Result"
            )


            Spacer(
                modifier =
                Modifier.height(8.dp)
            )


            Text(
                text =
                resultText
            )
        }
    }
}


// ==================================================
// Start Speech Recognition
// ==================================================

private fun startListening(

    speechRecognizer:
    SpeechRecognizer?,

    context:
    android.content.Context

) {


    // --------------------------------------------------
    // Check SpeechRecognizer
    // --------------------------------------------------

    if (
        speechRecognizer == null
    ) {

        Log.e(
            TAG,
            "Speech recognition is not available"
        )

        return
    }


    // --------------------------------------------------
    // Create speech recognition intent
    // --------------------------------------------------

    val intent =
        Intent(
            RecognizerIntent.ACTION_RECOGNIZE_SPEECH
        ).apply {


            putExtra(

                RecognizerIntent
                    .EXTRA_LANGUAGE_MODEL,

                RecognizerIntent
                    .LANGUAGE_MODEL_FREE_FORM
            )


            putExtra(

                RecognizerIntent
                    .EXTRA_LANGUAGE,

                Locale.getDefault()
            )


            putExtra(

                RecognizerIntent
                    .EXTRA_PARTIAL_RESULTS,

                false
            )
        }


    // --------------------------------------------------
    // Start listening
    // --------------------------------------------------

    try {

        speechRecognizer.startListening(
            intent
        )

    } catch (e: Exception) {

        Log.e(
            TAG,
            "Unable to start speech recognition",
            e
        )
    }
}


// ==================================================
// Preview
// ==================================================

@Preview(
    showBackground = true
)
@Composable
fun MeetingAIScreenPreview() {

    MeetingAITheme {

        MeetingAIScreen()
    }
}

