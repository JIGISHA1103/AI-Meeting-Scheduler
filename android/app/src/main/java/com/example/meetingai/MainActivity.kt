
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
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import org.json.JSONObject
import java.util.Locale
import java.util.concurrent.TimeUnit

private const val BASE_URL = "http://192.168.0.165:8000"

private const val TAG = "MeetingAI"

private val client = OkHttpClient.Builder()
    .connectTimeout(30, TimeUnit.SECONDS)
    .readTimeout(120, TimeUnit.SECONDS)
    .writeTimeout(30, TimeUnit.SECONDS)
    .build()

// --------------------------------------------------
// Format FastAPI scheduling response
// --------------------------------------------------

private fun formatScheduleResult(responseBody: String): String {

    return try {

        val json = JSONObject(responseBody)

        val status = json.optString("status")

        if (status == "success") {

            val meeting = json.optJSONObject("meeting")

            val title = meeting?.optString(
                "title",
                "Meeting"
            ) ?: "Meeting"

            val date = meeting?.optString(
                "date",
                ""
            ) ?: ""

            val time = meeting?.optString(
                "time",
                ""
            ) ?: ""

            val duration = meeting?.optInt(
                "duration",
                60
            ) ?: 60

            val participants =
                meeting?.optJSONArray("participants")

            val participantText = if (
                participants != null &&
                participants.length() > 0
            ) {

                buildString {

                    for (i in 0 until participants.length()) {

                        append(participants.optString(i))

                        if (i < participants.length() - 1) {
                            append(", ")
                        }
                    }
                }

            } else {

                "None"
            }

            buildString {

                append("Meeting Scheduled Successfully\n\n")

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

        } else if (status == "conflict") {

            val message = json.optString(
                "message",
                "The requested time is already occupied."
            )

            "Scheduling Conflict\n\n$message"

        } else if (status == "error") {

            val message = json.optString(
                "message",
                "Something went wrong while scheduling the meeting."
            )

            "Scheduling Error\n\n$message"

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

// --------------------------------------------------
// Main Activity
// --------------------------------------------------

class MainActivity : ComponentActivity() {

    override fun onCreate(savedInstanceState: Bundle?) {

        super.onCreate(savedInstanceState)

        enableEdgeToEdge()

        setContent {

            MeetingAITheme {

                MeetingAIScreen()
            }
        }
    }
}

// --------------------------------------------------
// Main UI + Speech-to-Text
// --------------------------------------------------

@Composable
fun MeetingAIScreen() {

    val context = LocalContext.current

    // --------------------------------------------------
    // Meeting request text
    // --------------------------------------------------

    var meetingText by remember {

        mutableStateOf("")
    }

    // --------------------------------------------------
    // Scheduling result
    // --------------------------------------------------

    var resultText by remember {

        mutableStateOf("")
    }

    // --------------------------------------------------
    // Loading state
    // --------------------------------------------------

    var isLoading by remember {

        mutableStateOf(false)
    }

    // --------------------------------------------------
    // Speech recognition state
    // --------------------------------------------------

    var isListening by remember {

        mutableStateOf(false)
    }

    // --------------------------------------------------
    // Create SpeechRecognizer
    // --------------------------------------------------

    val speechRecognizer = remember {

        if (SpeechRecognizer.isRecognitionAvailable(context)) {

            SpeechRecognizer.createSpeechRecognizer(context)

        } else {

            null
        }
    }

    // --------------------------------------------------
    // Speech recognition listener
    // --------------------------------------------------

    DisposableEffect(speechRecognizer) {

        if (speechRecognizer != null) {

            speechRecognizer.setRecognitionListener(

                object : RecognitionListener {

                    override fun onReadyForSpeech(
                        params: Bundle?
                    ) {

                        isListening = true

                        Log.d(
                            TAG,
                            "Speech recognition ready"
                        )
                    }

                    override fun onBeginningOfSpeech() {

                        isListening = true

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

                        isListening = false

                        Log.d(
                            TAG,
                            "Speech ended"
                        )
                    }

                    override fun onError(
                        error: Int
                    ) {

                        isListening = false

                        Log.e(
                            TAG,
                            "Speech recognition error: $error"
                        )
                    }

                    override fun onResults(
                        results: Bundle?
                    ) {

                        isListening = false

                        val matches =
                            results?.getStringArrayList(
                                SpeechRecognizer.RESULTS_RECOGNITION
                            )

                        if (!matches.isNullOrEmpty()) {

                            meetingText = matches[0]

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

        onDispose {

            speechRecognizer?.destroy()
        }
    }

    // --------------------------------------------------
    // Microphone permission launcher
    // --------------------------------------------------

    val microphonePermissionLauncher =
        rememberLauncherForActivityResult(
            ActivityResultContracts.RequestPermission()
        ) { granted ->

            if (granted) {

                startListening(
                    speechRecognizer = speechRecognizer,
                    context = context
                )

            } else {

                resultText =
                    "Microphone permission is required for voice input."
            }
        }

    // --------------------------------------------------
    // Scroll state
    // --------------------------------------------------

    val scrollState =
        rememberScrollState()

    // --------------------------------------------------
    // UI
    // --------------------------------------------------

    Scaffold(

        modifier = Modifier.fillMaxSize()

    ) { innerPadding ->

        Column(

            modifier = Modifier
                .fillMaxSize()
                .padding(innerPadding)
                .padding(24.dp)
                .verticalScroll(scrollState),

            horizontalAlignment =
            Alignment.CenterHorizontally,

            verticalArrangement =
            Arrangement.Center

        ) {

            Text(
                text = "Meeting AI",
                fontSize = 32.sp
            )

            Spacer(
                modifier = Modifier.height(8.dp)
            )

            Text(
                text = "Schedule a Meeting",
                fontSize = 20.sp
            )

            Spacer(
                modifier = Modifier.height(24.dp)
            )

            // --------------------------------------------------
            // Meeting request input
            // --------------------------------------------------

            OutlinedTextField(

                value = meetingText,

                onValueChange = {

                    meetingText = it
                },

                modifier = Modifier.fillMaxWidth(),

                label = {
                    Text("Meeting request")
                },

                placeholder = {

                    Text(
                        "Example: Schedule a project meeting tomorrow at 3 PM"
                    )
                },

                minLines = 4,

                keyboardOptions =
                KeyboardOptions(
                    keyboardType =
                    KeyboardType.Text
                )
            )

            Spacer(
                modifier = Modifier.height(16.dp)
            )

            // --------------------------------------------------
            // Microphone + Clear buttons
            // --------------------------------------------------

            Row(

                modifier = Modifier.fillMaxWidth(),

                horizontalArrangement =
                Arrangement.Center,

                verticalAlignment =
                Alignment.CenterVertically

            ) {

                // Microphone button
                IconButton(

                    onClick = {

                        if (isListening) {

                            speechRecognizer?.stopListening()

                            isListening = false

                        } else {

                            if (
                                context.checkSelfPermission(
                                    Manifest.permission.RECORD_AUDIO
                                ) == PackageManager.PERMISSION_GRANTED
                            ) {

                                startListening(
                                    speechRecognizer = speechRecognizer,
                                    context = context
                                )

                            } else {

                                microphonePermissionLauncher.launch(
                                    Manifest.permission.RECORD_AUDIO
                                )
                            }
                        }
                    },

                    modifier = Modifier.size(64.dp),

                    enabled = !isLoading

                ) {

                    Text(

                        text = if (isListening) {

                            "■"

                        } else {

                            "🎤"
                        },

                        fontSize = 32.sp
                    )
                }

                // Clear button
                TextButton(

                    onClick = {

                        meetingText = ""
                        resultText = ""

                    },

                    enabled = !isLoading

                ) {

                    Text(
                        text = "Clear"
                    )
                }
            }

            Text(

                text = if (isListening) {

                    "Listening..."

                } else {

                    "Tap microphone to speak"
                }
            )

            Spacer(
                modifier = Modifier.height(24.dp)
            )

            // --------------------------------------------------
            // Schedule Meeting button
            // --------------------------------------------------

            Button(

                onClick = {

                    if (meetingText.isBlank()) {

                        resultText =
                            "Please enter a meeting request."

                        return@Button
                    }

                    isLoading = true

                    resultText =
                        "Sending request..."

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

                            val json =
                                JSONObject()

                            json.put(
                                "text",
                                meetingText
                            )

                            val mediaType =
                                "application/json".toMediaType()

                            val requestBody =
                                json.toString()
                                    .toRequestBody(
                                        mediaType
                                    )

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
                                response.body?.string()
                                    ?: ""

                            Log.d(
                                TAG,
                                "FastAPI response code: ${response.code}"
                            )

                            Log.d(
                                TAG,
                                "FastAPI response: $responseBody"
                            )

                            withContext(
                                Dispatchers.Main
                            ) {

                                isLoading = false

                                if (response.isSuccessful) {

                                    resultText =
                                        formatScheduleResult(
                                            responseBody
                                        )

                                } else {

                                    resultText =
                                        "Server error ${response.code}: $responseBody"
                                }
                            }

                        } catch (e: Exception) {

                            Log.e(
                                TAG,
                                "FastAPI request failed",
                                e
                            )

                            withContext(
                                Dispatchers.Main
                            ) {

                                isLoading = false

                                resultText =
                                    "Connection error: ${e.message}"
                            }
                        }
                    }
                },

                modifier =
                Modifier.fillMaxWidth(),

                enabled = !isLoading

            ) {

                Text(

                    text = if (isLoading) {

                        "Scheduling..."

                    } else {

                        "Schedule Meeting"
                    }
                )
            }

            Spacer(
                modifier = Modifier.height(24.dp)
            )

            // --------------------------------------------------
            // Result
            // --------------------------------------------------

            Text(
                text = "Result"
            )

            Spacer(
                modifier = Modifier.height(8.dp)
            )

            Text(
                text = resultText
            )
        }
    }
}

// --------------------------------------------------
// Start Speech Recognition
// --------------------------------------------------

private fun startListening(
    speechRecognizer: SpeechRecognizer?,
    context: android.content.Context
) {

    if (speechRecognizer == null) {

        Log.e(
            TAG,
            "Speech recognition is not available"
        )

        return
    }

    val intent = Intent(
        RecognizerIntent.ACTION_RECOGNIZE_SPEECH
    ).apply {

        putExtra(
            RecognizerIntent.EXTRA_LANGUAGE_MODEL,
            RecognizerIntent.LANGUAGE_MODEL_FREE_FORM
        )

        putExtra(
            RecognizerIntent.EXTRA_LANGUAGE,
            Locale.getDefault()
        )

        putExtra(
            RecognizerIntent.EXTRA_PARTIAL_RESULTS,
            false
        )
    }

    try {

        speechRecognizer.startListening(intent)

    } catch (e: Exception) {

        Log.e(
            TAG,
            "Unable to start speech recognition",
            e
        )
    }
}

// --------------------------------------------------
// Preview
// --------------------------------------------------

@Preview(showBackground = true)
@Composable
fun MeetingAIScreenPreview() {

    MeetingAITheme {

        MeetingAIScreen()
    }
}
