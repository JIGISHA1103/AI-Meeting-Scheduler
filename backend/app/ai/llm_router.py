from app.ai.groq_parser import (
    parse_meeting_request_groq
)

from app.ai.parser import (
    parse_meeting_request
)


# --------------------------------------------------
# LLM Router
# --------------------------------------------------

def parse_meeting_request_with_fallback(
    user_input: str
):

    # --------------------------------------------------
    # PRIMARY: GROQ
    # --------------------------------------------------

    try:

        print(
            "\n========== LLM ROUTER =========="
        )

        print(
            "[Router] Trying Groq..."
        )

        print(
            "================================"
        )

        result = parse_meeting_request_groq(
            user_input
        )

        print(
            "[Router] Groq succeeded"
        )

        return result


    except Exception as groq_error:

        print(
            "\n========== GROQ FAILED =========="
        )

        print(
            f"[Router] Groq error: {groq_error}"
        )

        print(
            "[Router] Falling back to Gemini..."
        )

        print(
            "=================================\n"
        )


    # --------------------------------------------------
    # FALLBACK: GEMINI
    # --------------------------------------------------

    try:

        result = parse_meeting_request(
            user_input
        )

        print(
            "[Router] Gemini fallback succeeded"
        )

        return result


    except Exception as gemini_error:

        print(
            "\n========== ALL LLMs FAILED =========="
        )

        print(
            f"[Router] Gemini error: {gemini_error}"
        )

        print(
            "======================================"
        )

        raise RuntimeError(
            "Both Groq and Gemini failed."
        )