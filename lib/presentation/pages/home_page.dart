import 'package:beforedoctor/core/constants/colors.dart';
import 'package:beforedoctor/presentation/bloc/chat_cubit.dart';
import 'package:beforedoctor/presentation/bloc/chat_state.dart';
import 'package:beforedoctor/presentation/widgets/chat_messages.dart';
import 'package:beforedoctor/presentation/widgets/listening_overlay.dart';
import 'package:beforedoctor/presentation/widgets/text_input_overlay.dart';
import 'package:beforedoctor/presentation/widgets/transcript_editor_overlay.dart';
import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:slide_to_act/slide_to_act.dart';

class HomePage extends StatelessWidget {
  const HomePage({super.key});

  @override
  Widget build(BuildContext context) {
    return BlocProvider(
      create: (_) => ChatCubit(),
      child: const _HomeView(),
    );
  }
}

class _HomeView extends StatefulWidget {
  const _HomeView();

  @override
  State<_HomeView> createState() => _HomeViewState();
}

class _HomeViewState extends State<_HomeView> {
  final _transcriptController = TextEditingController();
  bool _transcriptSheetOpen = false;
  bool _listeningSheetOpen = false;
  String? _lastDraft;

  @override
  void dispose() {
    _transcriptController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: SafeArea(
        child: BlocConsumer<ChatCubit, ChatState>(
          listener: (context, state) {
            final draft = state.transcriptDraft;
            if (draft != null && draft != _transcriptController.text) {
              _transcriptController.text = draft;
            }
            if (draft == null && _transcriptController.text.isNotEmpty) {
              _transcriptController.clear();
            }
            if (draft == null) {
              _lastDraft = null;
            }
            if (!state.recording && _listeningSheetOpen) {
              Navigator.of(context).maybePop();
              _listeningSheetOpen = false;
            }
            if (state.recording && !_listeningSheetOpen) {
              _listeningSheetOpen = true;
              WidgetsBinding.instance.addPostFrameCallback((_) async {
                await showListeningOverlay(
                  context: context,
                  amplitudeStream:
                      context.read<ChatCubit>().amplitudeStream(
                            const Duration(milliseconds: 120),
                          ),
                  onStop: () {
                    context.read<ChatCubit>().stopRecording();
                    Navigator.pop(context);
                  },
                );
                if (context.mounted) {
                  _listeningSheetOpen = false;
                }
              });
            }
            if (draft != null && draft != _lastDraft && !_transcriptSheetOpen) {
              _transcriptSheetOpen = true;
              _lastDraft = draft;
              WidgetsBinding.instance.addPostFrameCallback((_) async {
                await showTranscriptOverlay(
                  context: context,
                  controller: _transcriptController,
                  onSend: () {
                    context.read<ChatCubit>().clearTranscriptDraft();
                    context
                        .read<ChatCubit>()
                        .sendMessage(_transcriptController.text);
                  },
                  onCancel: () {
                    context.read<ChatCubit>().clearTranscriptDraft();
                  },
                );
                if (context.mounted) {
                  _transcriptSheetOpen = false;
                }
              });
            }
          },
          builder: (context, state) {
            return Container(
              decoration: const BoxDecoration(
                gradient: LinearGradient(
                  colors: [Color(0xFFEFF6FF), Color(0xFFF7FBF8)],
                  begin: Alignment.topCenter,
                  end: Alignment.bottomCenter,
                ),
              ),
              child: Stack(
                children: [
                  Column(
                    children: [
                      const _Header(),
                      Expanded(
                        child: ChatMessages(
                          state: state,
                          bottomPadding: 140,
                        ),
                      ),
                    ],
                  ),
                  Positioned(
                    left: 20,
                    right: 20,
                    bottom: 24,
                    child: Row(
                      children: [
                        Expanded(
                          child: SlideAction(
                            height: 62,
                            borderRadius: 32,
                            outerColor: AppColors.primaryBlue,
                            innerColor: Colors.white,
                            text: 'Slide to talk',
                            textStyle: const TextStyle(
                              color: Colors.white,
                              fontWeight: FontWeight.w600,
                            ),
                            sliderButtonIcon: const Icon(
                              Icons.mic_none_rounded,
                              color: AppColors.primaryBlue,
                            ),
                            onSubmit: () {
                              context.read<ChatCubit>().startRecording();
                            },
                          ),
                        ),
                        const SizedBox(width: 12),
                        Expanded(
                          child: Directionality(
                            textDirection: TextDirection.rtl,
                            child: SlideAction(
                              height: 62,
                              borderRadius: 32,
                              outerColor: const Color(0xFF10243E),
                              innerColor: Colors.white,
                              text: 'Slide to type',
                              textStyle: const TextStyle(
                                color: Colors.white,
                                fontWeight: FontWeight.w600,
                              ),
                              sliderButtonIcon: const Icon(
                                Icons.chat_bubble_outline_rounded,
                                color: Color(0xFF10243E),
                              ),
                              onSubmit: () async {
                                final text =
                                    await showTextInputOverlay(context);
                                if (!context.mounted || text == null) {
                                  return;
                                }
                                context
                                    .read<ChatCubit>()
                                    .clearTranscriptDraft();
                                context.read<ChatCubit>().sendMessage(text);
                              },
                            ),
                          ),
                        ),
                      ],
                    ),
                  ),
                ],
              ),
            );
          },
        ),
      ),
    );
  }
}

class _Header extends StatelessWidget {
  const _Header();

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.fromLTRB(20, 16, 20, 8),
      child: Row(
        children: [
          Container(
            width: 48,
            height: 48,
            decoration: BoxDecoration(
              color: AppColors.primaryBlue,
              borderRadius: BorderRadius.circular(16),
            ),
            child: const Icon(Icons.local_hospital_rounded, color: Colors.white),
          ),
          const SizedBox(width: 14),
          Text(
            'Before Doctor',
            style: Theme.of(context).textTheme.headlineMedium?.copyWith(
                  fontSize: 24,
                ),
          ),
        ],
      ),
    );
  }
}
