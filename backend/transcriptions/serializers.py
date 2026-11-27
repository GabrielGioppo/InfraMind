from rest_framework import serializers

MAX_UPLOAD_BYTES = 10 * 1024 * 1024


class AudioUploadSerializer(serializers.Serializer):
    audio = serializers.FileField(
        allow_empty_file=False,
        error_messages={
            'required': 'Envie um arquivo de áudio.',
            'empty': 'O arquivo de áudio está vazio.',
            'invalid': 'Envie um arquivo de áudio válido.',
        },
    )

    def validate_audio(self, audio):
        if audio.size > MAX_UPLOAD_BYTES:
            raise serializers.ValidationError('O áudio deve ter até 10 MB.')
        return audio
