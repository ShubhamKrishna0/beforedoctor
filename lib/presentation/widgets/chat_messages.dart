import 'package:beforedoctor/features/ai_response/presentation/widgets/structured_response_card.dart';
import 'package:beforedoctor/features/chat/domain/entities/chat_message.dart';
import 'package:beforedoctor/presentation/bloc/chat_state.dart';
import 'package:flutter/material.dart';
import 'package:intl/intl.dart';


class ChatMessages extends StatefulWidget {
  const ChatMessages({
    super.key,
    required this.state,
    this.bottomPadding = 24,
  });

  final ChatState state;
  final double bottomPadding;

  @override
  State<ChatMessages> createState() => _ChatMessagesState();
}

class _ChatMessagesState extends State<ChatMessages> {
  final ScrollController _controller = ScrollController();
  int _lastCount = 0;

  @override
  void didUpdateWidget(covariant ChatMessages oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (widget.state.messages.length != _lastCount) {
      _lastCount = widget.state.messages.length;
      WidgetsBinding.instance.addPostFrameCallback((_) {
        if (_controller.hasClients) {
          _controller.animateTo(
            _controller.position.maxScrollExtent,
            duration: const Duration(milliseconds: 220),
            curve: Curves.easeOut,
          );
        }
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    final sorted = [...widget.state.messages]
      ..sort((a, b) => a.timestamp.compareTo(b.timestamp));
    return ListView(
      controller: _controller,
      padding: EdgeInsets.fromLTRB(20, 16, 20, widget.bottomPadding),
      children: [
        for (final entry in _groupByDay(sorted))
          if (entry is _DateHeader)
            _DateDivider(label: entry.label)
          else if (entry is ChatMessage)
            _MessageBubble(message: entry),
        if (widget.state.error != null)
          Padding(
            padding: const EdgeInsets.only(top: 16),
            child: Text(
              widget.state.error!,
              style: const TextStyle(color: Color(0xFFE15656)),
            ),
          ),
        if (widget.state.loading)
          const Padding(
            padding: EdgeInsets.only(top: 16),
            child: Center(child: CircularProgressIndicator()),
          ),
      ],
    );
  }
}

List<Object> _groupByDay(List<ChatMessage> messages) {
  final List<Object> grouped = [];
  final formatter = DateFormat.yMMMMd();
  DateTime? currentDay;
  for (final message in messages) {
    final day = DateTime(
      message.timestamp.year,
      message.timestamp.month,
      message.timestamp.day,
    );
    if (currentDay == null || day != currentDay) {
      currentDay = day;
      grouped.add(_DateHeader(formatter.format(day)));
    }
    grouped.add(message);
  }
  return grouped;
}

class _DateHeader {
  const _DateHeader(this.label);

  final String label;
}

class _DateDivider extends StatelessWidget {
  const _DateDivider({required this.label});

  final String label;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 12),
      child: Row(
        children: [
          const Expanded(child: Divider()),
          const SizedBox(width: 12),
          Text(
            label,
            style: Theme.of(context).textTheme.labelMedium?.copyWith(
                  color: const Color(0xFF7B8CA6),
                ),
          ),
          const SizedBox(width: 12),
          const Expanded(child: Divider()),
        ],
      ),
    );
  }
}

class _MessageBubble extends StatelessWidget {
  const _MessageBubble({required this.message});

  final ChatMessage message;

  @override
  Widget build(BuildContext context) {
    final isUser = message.role == 'user';
    final time = DateFormat.jm().format(message.timestamp);
    return Padding(
      padding: const EdgeInsets.only(bottom: 12),
      child: Align(
        alignment: isUser ? Alignment.centerRight : Alignment.centerLeft,
        child: Column(
          crossAxisAlignment:
              isUser ? CrossAxisAlignment.end : CrossAxisAlignment.start,
          children: [
            if (message.response != null)
              SizedBox(
                width: 320,
                child: StructuredResponseCard(response: message.response!),
              )
            else
              Container(
                constraints: const BoxConstraints(maxWidth: 280),
                padding: const EdgeInsets.all(14),
                decoration: BoxDecoration(
                  color: isUser
                      ? const Color(0xFF2276FF)
                      : const Color(0xFFEFF3F7),
                  borderRadius: BorderRadius.circular(18),
                ),
                child: Text(
                  message.text,
                  style: TextStyle(
                    color: isUser ? Colors.white : const Color(0xFF10243E),
                  ),
                ),
              ),
            const SizedBox(height: 4),
            Text(
              time,
              style: Theme.of(context).textTheme.labelSmall?.copyWith(
                    color: const Color(0xFF7B8CA6),
                  ),
            ),
          ],
        ),
      ),
    );
  }
}
