from django.conf import settings
from twilio.base.exceptions import TwilioRestException
from twilio.rest import Client

from .base import NotificationProvider, ProviderResult
from .exceptions import TransientProviderError


def _configured():
    return bool(
        settings.TWILIO_ACCOUNT_SID and settings.TWILIO_AUTH_TOKEN and settings.TWILIO_FROM_NUMBER
    )


def _client():
    return Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)


class TwilioSMSProvider(NotificationProvider):
    def send(self, user, incident, message):
        if not user.phone_number:
            return ProviderResult(success=False, error_message="User has no phone_number on file.")
        if not _configured():
            return ProviderResult(
                success=False, error_message="Twilio is not configured on this instance."
            )
        try:
            sms = _client().messages.create(
                body=message, from_=settings.TWILIO_FROM_NUMBER, to=user.phone_number
            )
        except TwilioRestException as exc:
            if exc.status and exc.status >= 500:
                raise TransientProviderError(str(exc)) from exc
            return ProviderResult(success=False, error_message=str(exc))
        return ProviderResult(success=True, provider_message_id=sms.sid)


class TwilioVoiceProvider(NotificationProvider):
    def send(self, user, incident, message):
        if not user.phone_number:
            return ProviderResult(success=False, error_message="User has no phone_number on file.")
        if not _configured():
            return ProviderResult(
                success=False, error_message="Twilio is not configured on this instance."
            )
        twiml = f"<Response><Say>{message}</Say></Response>"
        try:
            call = _client().calls.create(
                twiml=twiml, from_=settings.TWILIO_FROM_NUMBER, to=user.phone_number
            )
        except TwilioRestException as exc:
            if exc.status and exc.status >= 500:
                raise TransientProviderError(str(exc)) from exc
            return ProviderResult(success=False, error_message=str(exc))
        return ProviderResult(success=True, provider_message_id=call.sid)
