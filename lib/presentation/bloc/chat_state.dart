import 'package:beforedoctor/features/chat/domain/entities/chat_message.dart';
import 'package:beforedoctor/features/chat/domain/entities/doctor_response.dart';
import 'package:equatable/equatable.dart';

class ChatState extends Equatable {
  const ChatState({
    this.loading = false,
    this.recording = false,
    this.isPlaying = false,
    this.isMuted = false,
    this.recordingPath,
    this.latestResponse,
    this.transcriptDraft,
    this.lastUserMessage,
    this.error,
    this.messages = const [],
  });

  final bool loading;
  final bool recording;
  final bool isPlaying;
  final bool isMuted;
  final String? recordingPath;
  final DoctorResponse? latestResponse;
  final String? transcriptDraft;
  final String? lastUserMessage;
  final String? error;
  final List<ChatMessage> messages;

  ChatState copyWith({
    bool? loading,
    bool? recording,
    bool? isPlaying,
    bool? isMuted,
    String? recordingPath,
    DoctorResponse? latestResponse,
    String? transcriptDraft,
    String? lastUserMessage,
    String? error,
    List<ChatMessage>? messages,
  }) {
    return ChatState(
      loading: loading ?? this.loading,
      recording: recording ?? this.recording,
      isPlaying: isPlaying ?? this.isPlaying,
      isMuted: isMuted ?? this.isMuted,
      recordingPath: recordingPath ?? this.recordingPath,
      latestResponse: latestResponse ?? this.latestResponse,
      transcriptDraft: transcriptDraft ?? this.transcriptDraft,
      lastUserMessage: lastUserMessage ?? this.lastUserMessage,
      error: error,
      messages: messages ?? this.messages,
    );
  }

  @override
  List<Object?> get props => [
        loading,
        recording,
        isPlaying,
        isMuted,
        recordingPath,
        latestResponse,
        transcriptDraft,
        lastUserMessage,
        error,
        messages,
      ];
}
