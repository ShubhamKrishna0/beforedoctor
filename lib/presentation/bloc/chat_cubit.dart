import 'dart:io';

import 'package:beforedoctor/core/network/api_client.dart';
import 'package:beforedoctor/features/audio/data/repositories/audio_repository.dart';
import 'package:beforedoctor/features/chat/domain/entities/chat_message.dart';
import 'package:beforedoctor/features/chat/data/repositories/chat_repository.dart';
import 'package:beforedoctor/presentation/bloc/chat_state.dart';
import 'package:dio/dio.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:waveform_flutter/waveform_flutter.dart' as wave;
import 'package:path_provider/path_provider.dart';
import 'package:record/record.dart';

class ChatCubit extends Cubit<ChatState> {
  ChatCubit()
      : _chatRepository = ChatRepository(ApiClient()),
        _audioRepository = AudioRepository(ApiClient()),
        _record = AudioRecorder(),
        super(const ChatState());

  final ChatRepository _chatRepository;
  final AudioRepository _audioRepository;
  final AudioRecorder _record;
  int _transcriptionGeneration = 0;
  int? _activeTranscriptionGeneration;

  Stream<wave.Amplitude> amplitudeStream(Duration interval) {
    return _record.onAmplitudeChanged(interval).map(
          (amp) => wave.Amplitude(current: amp.current, max: amp.max),
        );
  }

  Future<void> sendMessage(String text) async {
    final message = text.trim();
    if (message.isEmpty) {
      emit(state.copyWith(error: 'Message cannot be empty.'));
      return;
    }
    _transcriptionGeneration++;
    _activeTranscriptionGeneration = null;
    final userMessage = ChatMessage(
      id: DateTime.now().microsecondsSinceEpoch.toString(),
      role: 'user',
      text: message,
      timestamp: DateTime.now(),
    );
    emit(
      state.copyWith(
        loading: true,
        error: null,
        transcriptDraft: null,
        recording: false,
        recordingPath: null,
        lastUserMessage: message,
        messages: [...state.messages, userMessage],
      ),
    );
    try {
      final response = await _chatRepository.sendMessage(message);
      final aiMessage = ChatMessage(
        id: DateTime.now().microsecondsSinceEpoch.toString(),
        role: 'assistant',
        text: response.summaryOfSymptoms,
        timestamp: DateTime.now(),
        response: response,
      );
      emit(
        state.copyWith(
          loading: false,
          latestResponse: response,
          messages: [...state.messages, aiMessage],
        ),
      );
    } catch (error) {
      emit(
        state.copyWith(
          loading: false,
          error: _readableError(error),
        ),
      );
    }
  }

  void setTranscriptDraft(String text) {
    emit(state.copyWith(transcriptDraft: text));
  }

  void clearTranscriptDraft() {
    _transcriptionGeneration++;
    _activeTranscriptionGeneration = null;
    emit(state.copyWith(transcriptDraft: null));
  }

  Future<void> toggleRecording() async {
    if (state.recording) {
      await _stopRecording();
    } else {
      await _startRecording();
    }
  }

  Future<void> startRecording() async {
    if (!state.recording) {
      await _startRecording();
    }
  }

  Future<void> stopRecording() async {
    if (state.recording) {
      await _stopRecording();
    }
  }

  void togglePlayPause() {
    emit(state.copyWith(isPlaying: !state.isPlaying));
  }

  void toggleMute() {
    emit(state.copyWith(isMuted: !state.isMuted));
  }

  Future<void> _startRecording() async {
    final hasPermission = await _record.hasPermission();
    if (!hasPermission) {
      emit(
        state.copyWith(
          error: 'Microphone permission is required to record audio.',
        ),
      );
      return;
    }

    final tempDir = await getTemporaryDirectory();
    final filePath =
        '${tempDir.path}/before_doctor_${DateTime.now().millisecondsSinceEpoch}.m4a';
    _activeTranscriptionGeneration = ++_transcriptionGeneration;
    await _record.start(
      const RecordConfig(encoder: AudioEncoder.aacLc),
      path: filePath,
    );
    emit(state.copyWith(recording: true, recordingPath: filePath, error: null));
  }

  Future<void> _stopRecording() async {
    final path = await _record.stop();
    emit(state.copyWith(recording: false));

    final recordingPath = path ?? state.recordingPath;
    if (recordingPath == null) {
      emit(state.copyWith(error: 'Recording failed. Please try again.'));
      return;
    }

    emit(state.copyWith(loading: true, error: null));
    final token = _activeTranscriptionGeneration;
    try {
      final response =
          await _audioRepository.transcribeAudio(File(recordingPath));
      if (token == null || token != _transcriptionGeneration) {
        emit(state.copyWith(loading: false));
        return;
      }
      final transcript =
          response['edited_text'] ?? response['original_text'] ?? '';
      if (transcript is String && transcript.isNotEmpty) {
        emit(
          state.copyWith(
            loading: false,
            transcriptDraft: transcript,
            recordingPath: null,
          ),
        );
      } else {
        emit(
          state.copyWith(
            loading: false,
            error: 'Transcription returned empty text.',
          ),
        );
      }
    } catch (error) {
      emit(
        state.copyWith(
          loading: false,
          error: _readableError(error),
        ),
      );
    }
  }

  String _readableError(Object error) {
    if (error is DioException) {
      final status = error.response?.statusCode;
      if (status != null) {
        return 'Request failed (HTTP $status). Check backend and keys.';
      }
      return 'Unable to reach backend. Check API_BASE_URL and Wi-Fi.';
    }
    return 'Unable to contact Before Doctor right now.';
  }
}
