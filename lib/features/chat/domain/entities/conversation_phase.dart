enum ConversationPhase {
  gathering,
  responding,
  followUp;

  static ConversationPhase fromString(String value) {
    switch (value) {
      case 'gathering':
        return ConversationPhase.gathering;
      case 'responding':
        return ConversationPhase.responding;
      case 'follow_up':
      case 'followUp':
        return ConversationPhase.followUp;
      default:
        return ConversationPhase.gathering;
    }
  }
}
