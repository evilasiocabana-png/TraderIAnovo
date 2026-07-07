//+------------------------------------------------------------------+
//| TraderIA Visual Signals                                          |
//| Read-only MT5 indicator. Draws signals produced by TraderIA.      |
//+------------------------------------------------------------------+
#property indicator_chart_window
#property indicator_plots 0
#property strict

input string SignalFileName = "traderia_visual_signals.json";
input int RefreshSeconds = 2;
input bool HideNativeTradeLevels = true;
input bool DrawThinPriceLabels = true;
input bool AutoAttachToOpenCharts = true;

string PREFIX = "TRADERIA_VISUAL_";
string LAST_VALID_CONTENT = "";
string LAST_PLAN_TEXT = "";
string LAST_SIGNAL_DRAW_KEY = "";
datetime LAST_CHART_POLICY_APPLIED = 0;

int OnInit()
{
   IndicatorSetString(INDICATOR_SHORTNAME, "TraderIAVisualSignals");
   ApplyChartVisualPolicy();
   DeleteTraderIAObjects();

   EventSetTimer(RefreshSeconds);
   DrawTraderIASignals();
   return(INIT_SUCCEEDED);
}

void OnDeinit(const int reason)
{
   EventKillTimer();
   DeleteTraderIAObjects();
   Comment("");
}

void OnTimer()
{
   ApplyChartVisualPolicy();
   DrawTraderIASignals();
}

void ApplyChartVisualPolicy()
{
   if(LAST_CHART_POLICY_APPLIED > 0 && TimeCurrent() - LAST_CHART_POLICY_APPLIED < 60)
      return;

   long chart_id = ChartFirst();
   while(chart_id >= 0)
   {
      if(AutoAttachToOpenCharts)
         AttachTraderIAIndicatorIfMissing(chart_id);
      if(HideNativeTradeLevels)
      {
         ChartSetInteger(chart_id, CHART_SHOW_TRADE_LEVELS, false);
         ChartSetInteger(chart_id, CHART_SHOW_TRADE_HISTORY, false);
      }
      ChartRedraw(chart_id);
      chart_id = ChartNext(chart_id);
   }
   LAST_CHART_POLICY_APPLIED = TimeCurrent();
}

void AttachTraderIAIndicatorIfMissing(long chart_id)
{
   if(chart_id == 0 || chart_id == ChartID())
      return;
   if(IsTraderIAIndicatorAttached(chart_id))
      return;

   string symbol = ChartSymbol(chart_id);
   ENUM_TIMEFRAMES period = (ENUM_TIMEFRAMES)ChartPeriod(chart_id);
   if(symbol == "" || period <= 0)
      return;

   int handle = iCustom(
      symbol,
      period,
      "TraderIAVisualSignals",
      SignalFileName,
      RefreshSeconds,
      HideNativeTradeLevels,
      DrawThinPriceLabels,
      AutoAttachToOpenCharts
   );
   if(handle == INVALID_HANDLE)
      return;

   ChartIndicatorAdd(chart_id, 0, handle);
   IndicatorRelease(handle);
}

bool IsTraderIAIndicatorAttached(long chart_id)
{
   int total = ChartIndicatorsTotal(chart_id, 0);
   for(int i = 0; i < total; i++)
   {
      string name = ChartIndicatorName(chart_id, 0, i);
      if(StringFind(name, "TraderIAVisualSignals") >= 0)
         return(true);
      if(StringFind(name, "TraderIA Visual Signals") >= 0)
         return(true);
   }
   return(false);
}

int OnCalculate(
   const int rates_total,
   const int prev_calculated,
   const datetime &time[],
   const double &open[],
   const double &high[],
   const double &low[],
   const double &close[],
   const long &tick_volume[],
   const long &volume[],
   const int &spread[]
)
{
   return(rates_total);
}

void DrawTraderIASignals()
{
   string content = ReadSignalFile();
   if(content == "")
   {
      if(LAST_VALID_CONTENT == "")
      {
         Comment("TraderIA Visual Signals\nArquivo nao encontrado ou vazio: " + SignalFileName);
         return;
      }
      content = LAST_VALID_CONTENT;
   }
   else if(StringFind(content, "\"signals\"") < 0)
   {
      if(LAST_VALID_CONTENT == "")
      {
         Comment("TraderIA Visual Signals\nArquivo visual ainda incompleto: " + SignalFileName);
         return;
      }
      content = LAST_VALID_CONTENT;
   }
   else
   {
      LAST_VALID_CONTENT = content;
   }

   Comment("");

   string signal_content = ExtractTopLevelArraySection(content, "signals");
   string history_content = ExtractTopLevelArraySection(content, "signal_history");
   if(IsVisualDisabled(content, signal_content, history_content))
   {
      DeleteTraderIAObjects();
      Comment("");
      return;
   }

   if(signal_content == "")
      signal_content = content;

   DeleteTraderIAObjects();

   string chart_timeframe = ChartTimeframeLabel();

   bool matched_symbol = false;
   bool matched_timeframe = false;
   string first_signal_timeframe = "";

   int search_from = 0;
   int index = 0;
   while(true)
   {
      int symbol_pos = StringFind(signal_content, "\"symbol\"", search_from);
      if(symbol_pos < 0)
         break;

      int next_symbol_pos = StringFind(signal_content, "\"symbol\"", symbol_pos + 8);
      string block = "";
      if(next_symbol_pos < 0)
         block = StringSubstr(signal_content, symbol_pos);
      else
         block = StringSubstr(signal_content, symbol_pos, next_symbol_pos - symbol_pos);

      string symbol = ExtractJsonString(block, "symbol");
      if(symbol == _Symbol)
      {
         matched_symbol = true;
         string signal_timeframe = ExtractJsonString(block, "timeframe");
         if(first_signal_timeframe == "" && signal_timeframe != "")
            first_signal_timeframe = signal_timeframe;

         if(IsPositionedTradeBlock(block))
         {
            DrawStatusLabel(block, 0);
            DrawSignalBlock(block, 0);
            return;
         }

         if(signal_timeframe == chart_timeframe)
         {
            matched_timeframe = true;
            return;
         }
      }

      index++;
      if(next_symbol_pos < 0)
         break;
      search_from = next_symbol_pos;
   }

   if(matched_symbol && !matched_timeframe)
   {
      Comment("");
   }

   if(!matched_symbol)
   {
      Comment("");
   }
}

bool IsVisualDisabled(string content, string signal_content, string history_content)
{
   if(StringFind(content, "\"mode\"") >= 0 && StringFind(content, "VISUAL_DISABLED") >= 0)
      return(true);
   if(IsEmptyJsonArray(signal_content) && IsEmptyJsonArray(history_content))
      return(true);
   return(false);
}

bool IsEmptyJsonArray(string value)
{
   string normalized = value;
   StringReplace(normalized, " ", "");
   StringReplace(normalized, "\r", "");
   StringReplace(normalized, "\n", "");
   StringReplace(normalized, "\t", "");
   return(normalized == "[]");
}

bool IsDrawableTradeBlock(string block)
{
   if(block == "")
      return(false);
   string decision = ResolveVisualDecision(block);
   double entry = ExtractJsonNumber(block, "entry");
   return((decision == "BUY" || decision == "SELL") && entry > 0.0);
}

bool IsPositionedTradeBlock(string block)
{
   if(!IsDrawableTradeBlock(block))
      return(false);
   return(ExtractJsonString(block, "robot_status") == "POSICAO_ABERTA_MT5");
}

string FindLatestDrawableSymbolBlock(string section, string target_symbol)
{
   if(section == "")
      return("");

   string latest = "";
   string latest_order = "";
   string latest_position = "";
   int search_from = 0;
   while(true)
   {
      int symbol_pos = StringFind(section, "\"symbol\"", search_from);
      if(symbol_pos < 0)
         break;

      int next_symbol_pos = StringFind(section, "\"symbol\"", symbol_pos + 8);
      string block = "";
      if(next_symbol_pos < 0)
         block = StringSubstr(section, symbol_pos);
      else
         block = StringSubstr(section, symbol_pos, next_symbol_pos - symbol_pos);

      string symbol = ExtractJsonString(block, "symbol");
      if(symbol == target_symbol && IsDrawableTradeBlock(block))
      {
         string robot_status = ExtractJsonString(block, "robot_status");
         if(robot_status == "POSICAO_ABERTA_MT5")
            latest_position = block;
         else if(robot_status == "ORDEM_ENVIADA_DEMO")
            latest_order = block;
         else
            latest = block;
      }

      if(next_symbol_pos < 0)
         break;
      search_from = next_symbol_pos;
   }

   if(latest_position != "")
      return(latest_position);
   if(latest_order != "")
      return(latest_order);
   return(latest);
}

string FindLatestMatchingBlock(string section, string target_symbol, string target_timeframe)
{
   if(section == "")
      return("");

   string latest = "";
   string latest_order = "";
   string latest_position = "";
   int search_from = 0;
   while(true)
   {
      int symbol_pos = StringFind(section, "\"symbol\"", search_from);
      if(symbol_pos < 0)
         break;

      int next_symbol_pos = StringFind(section, "\"symbol\"", symbol_pos + 8);
      string block = "";
      if(next_symbol_pos < 0)
         block = StringSubstr(section, symbol_pos);
      else
         block = StringSubstr(section, symbol_pos, next_symbol_pos - symbol_pos);

      string symbol = ExtractJsonString(block, "symbol");
      string timeframe = ExtractJsonString(block, "timeframe");
      if(symbol == target_symbol && timeframe == target_timeframe)
      {
         string robot_status = ExtractJsonString(block, "robot_status");
         if(IsDrawableTradeBlock(block) && robot_status == "POSICAO_ABERTA_MT5")
            latest_position = block;
         else if(IsDrawableTradeBlock(block) && robot_status == "ORDEM_ENVIADA_DEMO")
            latest_order = block;
         else
            latest = block;
      }

      if(next_symbol_pos < 0)
         break;
      search_from = next_symbol_pos;
   }

   if(latest_position != "")
      return(latest_position);
   if(latest_order != "")
      return(latest_order);
   return(latest);
}

string ExtractTopLevelArraySection(string content, string key)
{
   string pattern = "\"" + key + "\"";
   int key_pos = StringFind(content, pattern);
   if(key_pos < 0)
      return("");

   int array_start = StringFind(content, "[", key_pos);
   if(array_start < 0)
      return("");

   int depth = 0;
   bool in_string = false;
   bool escaped = false;
   for(int i = array_start; i < StringLen(content); i++)
   {
      ushort ch = StringGetCharacter(content, i);
      if(escaped)
      {
         escaped = false;
         continue;
      }
      if(ch == '\\')
      {
         escaped = true;
         continue;
      }
      if(ch == '"')
      {
         in_string = !in_string;
         continue;
      }
      if(in_string)
         continue;
      if(ch == '[')
         depth++;
      else if(ch == ']')
      {
         depth--;
         if(depth == 0)
            return(StringSubstr(content, array_start, i - array_start + 1));
      }
   }

   return("");
}

string ReadSignalFile()
{
   int handle = FileOpen(
      SignalFileName,
      FILE_READ | FILE_TXT | FILE_ANSI | FILE_SHARE_READ | FILE_SHARE_WRITE
   );
   if(handle == INVALID_HANDLE)
      return("");

   string content = "";
   while(!FileIsEnding(handle))
      content += FileReadString(handle) + "\n";

   FileClose(handle);
   return(content);
}

void DrawSignalBlock(string block, int index)
{
   string signal_timeframe = ExtractJsonString(block, "timeframe");

   string decision = ResolveVisualDecision(block);
   if(decision == "WAIT")
      return;

   double entry = ExtractJsonNumber(block, "entry");
   double stop = ExtractJsonNumber(block, "stop");
   double target = ExtractJsonNumber(block, "target");
   double rr = ExtractJsonNumber(block, "rr");
   double score = ExtractJsonNumber(block, "score");
   double confidence = ExtractJsonNumber(block, "confidence");
   string model = ExtractJsonString(block, "model");
   string plan_status = ExtractJsonString(block, "plan_status");
   string robot_status = ExtractJsonString(block, "robot_status");
   string reason = ExtractJsonString(block, "reason");
   string operational_plan_text = DecodeJsonText(ExtractJsonString(block, "operational_plan_text"));
   string stop_management = ExtractJsonString(block, "stop_management");

   if(entry <= 0.0)
      return;

   string draw_key = (
      _Symbol + "|" +
      ChartTimeframeLabel() + "|" +
      signal_timeframe + "|" +
      decision + "|" +
      DoubleToString(entry, _Digits) + "|" +
      DoubleToString(stop, _Digits) + "|" +
      DoubleToString(target, _Digits) + "|" +
      ExtractJsonString(block, "timestamp") + "|" +
      ExtractJsonString(block, "position_open_time") + "|" +
      ExtractJsonString(block, "robot_status")
   );
   if(draw_key == LAST_SIGNAL_DRAW_KEY)
      return;
   LAST_SIGNAL_DRAW_KEY = draw_key;

   datetime signal_time = GetVisibleSignalTime();
   string timestamp = ExtractJsonString(block, "position_open_time");
   if(timestamp == "" || timestamp == "N/D")
      timestamp = ExtractJsonString(block, "timestamp");
   if(timestamp != "" && timestamp != "N/D")
   {
      datetime parsed_time = ParseTraderIATime(timestamp);
      if(parsed_time > 0)
         signal_time = parsed_time;
   }

   if(robot_status != "POSICAO_ABERTA_MT5" && !IsTimeVisible(signal_time))
      signal_time = GetVisibleSignalTime();

   color arrow_color = DecisionColor(decision);
   int arrow_code = DecisionArrowCode(decision);

   string suffix = IntegerToString(index);
   string arrow_name = PREFIX + "ARROW_" + suffix;
   if(ObjectFind(0, arrow_name) < 0)
      ObjectCreate(0, arrow_name, OBJ_ARROW, 0, signal_time, entry);
   else
      ObjectMove(0, arrow_name, 0, signal_time, entry);
   ObjectSetInteger(0, arrow_name, OBJPROP_ARROWCODE, arrow_code);
   ObjectSetInteger(0, arrow_name, OBJPROP_COLOR, arrow_color);
   ObjectSetInteger(0, arrow_name, OBJPROP_WIDTH, 2);

   DrawHorizontalLine(PREFIX + "ENTRY_" + suffix, entry, clrDeepSkyBlue, STYLE_SOLID);
   DrawPriceLevelLabel(PREFIX + "ENTRY_LABEL_" + suffix, decision, entry, clrDeepSkyBlue);
   if(stop > 0.0)
   {
      DrawHorizontalLine(PREFIX + "STOP_" + suffix, stop, clrRed, STYLE_SOLID);
      DrawPriceLevelLabel(PREFIX + "STOP_LABEL_" + suffix, "SL", stop, clrRed);
   }
   if(target > 0.0)
   {
      DrawHorizontalLine(PREFIX + "TARGET_" + suffix, target, clrLime, STYLE_SOLID);
      DrawPriceLevelLabel(PREFIX + "TARGET_LABEL_" + suffix, "TP", target, clrLime);
   }

}

void DrawStatusLabel(string block, int index)
{
   string decision = ResolveVisualDecision(block);
   string model = ExtractJsonString(block, "model");
   string plan_status = ExtractJsonString(block, "plan_status");
   string reason = ExtractJsonString(block, "reason");
   double entry = ExtractJsonNumber(block, "entry");
   double stop = ExtractJsonNumber(block, "stop");
   double target = ExtractJsonNumber(block, "target");
   double rr = ExtractJsonNumber(block, "rr");
   double score = ExtractJsonNumber(block, "score");
   double confidence = ExtractJsonNumber(block, "confidence");
   string robot_status = ExtractJsonString(block, "robot_status");
   string operational_plan_text = DecodeJsonText(ExtractJsonString(block, "operational_plan_text"));
   string stop_management = ExtractJsonString(block, "stop_management");
   string signal_timeframe = ExtractJsonString(block, "timeframe");
   string dynamic_exit_visual_text = DecodeJsonText(ExtractJsonString(block, "dynamic_exit_visual_text"));

   string text = CompactPlanText(
      model,
      decision,
      reason,
      stop_management,
      rr,
      signal_timeframe,
      ChartTimeframeLabel(),
      dynamic_exit_visual_text
   );

   DrawOperationalPlanComment(text);
}

void DrawOperationalPlanComment(string text)
{
   if(text == LAST_PLAN_TEXT && PlanLabelsExist(text))
      return;
   LAST_PLAN_TEXT = text;

   Comment("");

   string remaining = text;
   int line_index = 0;
   while(StringLen(remaining) > 0 && line_index < 8)
   {
      int newline_pos = StringFind(remaining, "\n");
      string line = "";
      if(newline_pos < 0)
      {
         line = remaining;
         remaining = "";
      }
      else
      {
         line = StringSubstr(remaining, 0, newline_pos);
         remaining = StringSubstr(remaining, newline_pos + 1);
      }

      string label_name = PREFIX + "COMPACT_PLAN_LABEL_" + IntegerToString(line_index);
      if(ObjectFind(0, label_name) < 0)
         ObjectCreate(0, label_name, OBJ_LABEL, 0, 0, 0);

      ObjectSetInteger(0, label_name, OBJPROP_CORNER, CORNER_LEFT_LOWER);
      ObjectSetInteger(0, label_name, OBJPROP_XDISTANCE, 12);
      ObjectSetInteger(0, label_name, OBJPROP_YDISTANCE, 84 - line_index * 16);
      ObjectSetInteger(0, label_name, OBJPROP_COLOR, clrWhite);
      ObjectSetInteger(0, label_name, OBJPROP_FONTSIZE, 9);
      ObjectSetInteger(0, label_name, OBJPROP_BACK, false);
      ObjectSetInteger(0, label_name, OBJPROP_SELECTABLE, false);
      ObjectSetInteger(0, label_name, OBJPROP_SELECTED, false);
      ObjectSetInteger(0, label_name, OBJPROP_ZORDER, 1000);
      ObjectSetString(0, label_name, OBJPROP_TEXT, line);
      line_index++;
   }

   for(int clear_index = line_index; clear_index < 8; clear_index++)
   {
      string clear_name = PREFIX + "COMPACT_PLAN_LABEL_" + IntegerToString(clear_index);
      if(ObjectFind(0, clear_name) >= 0)
         ObjectSetString(0, clear_name, OBJPROP_TEXT, "");
   }
}

bool PlanLabelsExist(string text)
{
   int expected_lines = CountPlanLines(text);
   if(expected_lines <= 0)
      return(false);

   for(int index = 0; index < expected_lines && index < 8; index++)
   {
      string label_name = PREFIX + "COMPACT_PLAN_LABEL_" + IntegerToString(index);
      if(ObjectFind(0, label_name) < 0)
         return(false);
   }
   return(true);
}

int CountPlanLines(string text)
{
   if(text == "")
      return(0);

   int count = 1;
   int search_from = 0;
   while(true)
   {
      int newline_pos = StringFind(text, "\n", search_from);
      if(newline_pos < 0)
         break;
      count++;
      search_from = newline_pos + 1;
   }
   return(count);
}

string CompactPlanText(
   string model,
   string decision,
   string reason,
   string stop_management,
   double rr,
   string signal_timeframe,
   string chart_timeframe,
   string dynamic_exit_visual_text
)
{
   string timeframe_text = ValueOrNA(signal_timeframe);
   if(chart_timeframe != "" && signal_timeframe != "" && chart_timeframe != signal_timeframe)
      timeframe_text = timeframe_text + " (grafico " + chart_timeframe + ")";

   string text = (
      "Setup: " + ValueOrNA(model) + "\n" +
      "Tempo: " + timeframe_text + "\n" +
      "Entrada: " + ValueOrNA(decision) + "\n" +
      "Motivo: " + CompactEntryReason(reason) + "\n" +
      "Saida: " + ExitSummary(stop_management, rr)
   );

   dynamic_exit_visual_text = NormalizeOneLine(dynamic_exit_visual_text);
   if(dynamic_exit_visual_text != "")
      text = text + "\n" + LimitText(dynamic_exit_visual_text, 140);

   return(text);
}

string CompactEntryReason(string reason)
{
   string text = reason;
   if(text == "")
      return("N/A");

   int colon_pos = -1;
   int search_from = 0;
   while(true)
   {
      int found = StringFind(text, ":", search_from);
      if(found < 0)
         break;
      colon_pos = found;
      search_from = found + 1;
   }

   if(colon_pos >= 0 && colon_pos + 1 < StringLen(text))
      text = StringSubstr(text, colon_pos + 1);

   text = NormalizeOneLine(text);
   return(LimitText(text, 120));
}

string ExitSummary(string stop_management, double rr)
{
   string exit_model = ValueOrNA(stop_management);
   if(rr > 0.0)
      return(exit_model + " | RR " + DoubleToString(rr, 2));
   return(exit_model);
}

string ValueOrNA(string value)
{
   string text = NormalizeOneLine(value);
   if(text == "")
      return("N/A");
   return(text);
}

string NormalizeOneLine(string value)
{
   string text = value;
   StringReplace(text, "\r", " ");
   StringReplace(text, "\n", " ");
   while(StringFind(text, "  ") >= 0)
      StringReplace(text, "  ", " ");
   return(text);
}

string LimitText(string value, int max_length)
{
   if(StringLen(value) <= max_length)
      return(value);
   return(StringSubstr(value, 0, max_length - 3) + "...");
}

void DrawOperationalPlanLabel(string operational_plan_text, string reason, string decision)
{
   string text = operational_plan_text;
   if(text == "")
      text = reason;
   if(text == "")
      text = "N/A";

   string remaining = text;
   int line_index = 0;
   while(StringLen(remaining) > 0 && line_index < 32)
   {
      int newline_pos = StringFind(remaining, "\n");
      string line = "";
      if(newline_pos < 0)
      {
         line = remaining;
         remaining = "";
      }
      else
      {
         line = StringSubstr(remaining, 0, newline_pos);
         remaining = StringSubstr(remaining, newline_pos + 1);
      }

      string label_name = PREFIX + "OPERATIONAL_PLAN_LABEL_" + IntegerToString(line_index);
      if(ObjectFind(0, label_name) < 0)
         ObjectCreate(0, label_name, OBJ_LABEL, 0, 0, 0);

      ObjectSetInteger(0, label_name, OBJPROP_CORNER, CORNER_LEFT_UPPER);
      ObjectSetInteger(0, label_name, OBJPROP_XDISTANCE, 12);
      ObjectSetInteger(0, label_name, OBJPROP_YDISTANCE, 48 + line_index * 13);
      ObjectSetInteger(0, label_name, OBJPROP_COLOR, DecisionColor(decision));
      ObjectSetInteger(0, label_name, OBJPROP_FONTSIZE, 8);
      ObjectSetInteger(0, label_name, OBJPROP_BACK, false);
      ObjectSetInteger(0, label_name, OBJPROP_SELECTABLE, false);
      ObjectSetInteger(0, label_name, OBJPROP_ZORDER, 1000);
      ObjectSetString(0, label_name, OBJPROP_TEXT, line == "" ? " " : line);
      ObjectSetString(0, label_name, OBJPROP_TOOLTIP, text);
      line_index++;
   }
}

string TooltipOrReason(string operational_plan_text, string reason)
{
   if(operational_plan_text != "")
      return(operational_plan_text);
   return(reason);
}

string ResolveVisualDecision(string block)
{
   string decision = ExtractJsonString(block, "decision");
   if(decision == "BUY" || decision == "SELL")
      return(decision);

   string theoretical_direction = ExtractJsonString(block, "theoretical_entry_direction");
   double entry = ExtractJsonNumber(block, "entry");
   if((theoretical_direction == "BUY" || theoretical_direction == "SELL") && entry > 0.0)
      return(theoretical_direction);

   return("WAIT");
}

color DecisionColor(string decision)
{
   if(decision == "BUY")
      return(clrLime);
   if(decision == "SELL")
      return(clrRed);
   return(clrWhite);
}

int DecisionArrowCode(string decision)
{
   if(decision == "BUY")
      return(233);
   return(234);
}

void DrawTimeframeMismatchLabel(string signal_timeframe, string chart_timeframe)
{
   string label_name = PREFIX + "STATUS_LABEL";
   string text = "TraderIA | " + _Symbol +
                 " | Sinal disponivel em " + signal_timeframe +
                 ", grafico atual " + chart_timeframe;

   if(ObjectFind(0, label_name) < 0)
      ObjectCreate(0, label_name, OBJ_LABEL, 0, 0, 0);

   ObjectSetInteger(0, label_name, OBJPROP_CORNER, CORNER_LEFT_UPPER);
   ObjectSetInteger(0, label_name, OBJPROP_XDISTANCE, 12);
   ObjectSetInteger(0, label_name, OBJPROP_YDISTANCE, 24);
   ObjectSetInteger(0, label_name, OBJPROP_COLOR, clrSilver);
   ObjectSetInteger(0, label_name, OBJPROP_FONTSIZE, 9);
   ObjectSetString(0, label_name, OBJPROP_TEXT, text);
   ObjectSetString(0, label_name, OBJPROP_TOOLTIP, "O indicador so plota quando symbol e timeframe do JSON coincidem com o grafico.");
}

string PriceOrNA(double value)
{
   if(value <= 0.0)
      return("N/D");
   return(DoubleToString(value, _Digits));
}

string ChartTimeframeLabel()
{
   switch(_Period)
   {
      case PERIOD_M1:
         return("M1");
      case PERIOD_M2:
         return("M2");
      case PERIOD_M3:
         return("M3");
      case PERIOD_M4:
         return("M4");
      case PERIOD_M5:
         return("M5");
      case PERIOD_M6:
         return("M6");
      case PERIOD_M10:
         return("M10");
      case PERIOD_M12:
         return("M12");
      case PERIOD_M15:
         return("M15");
      case PERIOD_M20:
         return("M20");
      case PERIOD_M30:
         return("M30");
      case PERIOD_H1:
         return("H1");
      case PERIOD_H2:
         return("H2");
      case PERIOD_H3:
         return("H3");
      case PERIOD_H4:
         return("H4");
      case PERIOD_H6:
         return("H6");
      case PERIOD_H8:
         return("H8");
      case PERIOD_H12:
         return("H12");
      case PERIOD_D1:
         return("D1");
      case PERIOD_W1:
         return("W1");
      case PERIOD_MN1:
         return("MN1");
      default:
         return(IntegerToString(_Period));
   }
}

void DrawHorizontalLine(string name, double price, color line_color, ENUM_LINE_STYLE style)
{
   int first_visible = (int)ChartGetInteger(0, CHART_FIRST_VISIBLE_BAR);
   int visible_bars = (int)ChartGetInteger(0, CHART_VISIBLE_BARS);
   int right_index = MathMax(first_visible - visible_bars + 1, 0);
   int segment_bars = MathMax(visible_bars / 6, 12);
   int left_index = MathMin(right_index + segment_bars, first_visible);
   datetime left_time = iTime(_Symbol, _Period, left_index);
   datetime right_time = iTime(_Symbol, _Period, right_index);

   if(left_time <= 0)
      left_time = TimeCurrent() - PeriodSeconds(_Period) * 120;
   if(right_time <= 0 || right_time <= left_time)
      right_time = TimeCurrent() + PeriodSeconds(_Period) * 10;

   if(ObjectFind(0, name) < 0)
      ObjectCreate(0, name, OBJ_TREND, 0, left_time, price, right_time, price);
   else
   {
      ObjectMove(0, name, 0, left_time, price);
      ObjectMove(0, name, 1, right_time, price);
   }
   ObjectSetInteger(0, name, OBJPROP_COLOR, line_color);
   ObjectSetInteger(0, name, OBJPROP_STYLE, style);
   ObjectSetInteger(0, name, OBJPROP_WIDTH, 1);
   ObjectSetInteger(0, name, OBJPROP_RAY_LEFT, false);
   ObjectSetInteger(0, name, OBJPROP_RAY_RIGHT, false);
   ObjectSetInteger(0, name, OBJPROP_SELECTABLE, false);
   ObjectSetInteger(0, name, OBJPROP_SELECTED, false);
   ObjectSetInteger(0, name, OBJPROP_BACK, true);
}

void DrawPriceLevelLabel(string name, string label, double price, color label_color)
{
   if(!DrawThinPriceLabels || price <= 0.0)
      return;

   datetime label_time = GetVisibleRightTime();
   string text = label + " " + PriceOrNA(price);

   if(ObjectFind(0, name) < 0)
      ObjectCreate(0, name, OBJ_TEXT, 0, label_time, price);
   else
      ObjectMove(0, name, 0, label_time, price);
   ObjectSetInteger(0, name, OBJPROP_COLOR, label_color);
   ObjectSetInteger(0, name, OBJPROP_FONTSIZE, 8);
   ObjectSetInteger(0, name, OBJPROP_ANCHOR, ANCHOR_LEFT);
   ObjectSetInteger(0, name, OBJPROP_SELECTABLE, false);
   ObjectSetInteger(0, name, OBJPROP_SELECTED, false);
   ObjectSetInteger(0, name, OBJPROP_BACK, false);
   ObjectSetInteger(0, name, OBJPROP_ZORDER, 1000);
   ObjectSetString(0, name, OBJPROP_TEXT, text);
   ObjectSetString(0, name, OBJPROP_TOOLTIP, text);
}

datetime GetVisibleRightTime()
{
   int first_visible = (int)ChartGetInteger(0, CHART_FIRST_VISIBLE_BAR);
   int visible_bars = (int)ChartGetInteger(0, CHART_VISIBLE_BARS);
   int right_index = MathMax(first_visible - visible_bars + 1, 0);
   datetime right_time = iTime(_Symbol, _Period, right_index);
   if(right_time <= 0)
      right_time = TimeCurrent();

   return(right_time);
}

void DeleteTraderIAObjects()
{
   LAST_PLAN_TEXT = "";
   LAST_SIGNAL_DRAW_KEY = "";
   DeleteTraderIAObjectsOnChart(0);
}

void DeleteTraderIAObjectsOnChart(long chart_id)
{
   int total = ObjectsTotal(chart_id, 0, -1);
   for(int i = total - 1; i >= 0; i--)
   {
      string name = ObjectName(chart_id, i, 0, -1);
      if(IsTraderIAObject(name))
         ObjectDelete(chart_id, name);
   }
}

bool IsTraderIAObject(string name)
{
   if(StringFind(name, PREFIX) == 0)
      return(true);
   if(StringFind(name, "TRADERIA") >= 0)
      return(true);
   if(StringFind(name, "TraderIA") >= 0)
      return(true);
   if(StringFind(name, "traderia") >= 0)
      return(true);
   if(StringFind(name, "OPERATIONAL_PLAN_LABEL_") >= 0)
      return(true);
   if(StringFind(name, "COMPACT_PLAN_LABEL_") >= 0)
      return(true);

   string text = ObjectGetString(0, name, OBJPROP_TEXT);
   if(IsTraderIAText(text))
      return(true);
   string tooltip = ObjectGetString(0, name, OBJPROP_TOOLTIP);
   if(IsTraderIAText(tooltip))
      return(true);
   return(false);
}

bool IsTraderIAText(string text)
{
   if(text == "")
      return(false);
   if(StringFind(text, "TraderIA") >= 0)
      return(true);
   if(StringFind(text, "Setup:") >= 0)
      return(true);
   if(StringFind(text, "Tempo:") >= 0)
      return(true);
   if(StringFind(text, "Entrada:") >= 0)
      return(true);
   if(StringFind(text, "Motivo:") >= 0)
      return(true);
   if(StringFind(text, "Saida:") >= 0)
      return(true);
   if(StringFind(text, "SL ") == 0)
      return(true);
   if(StringFind(text, "TP ") == 0)
      return(true);
   if(StringFind(text, "BUY ") == 0)
      return(true);
   if(StringFind(text, "SELL ") == 0)
      return(true);
   return(false);
}

string ExtractJsonString(string block, string key)
{
   string pattern = "\"" + key + "\"";
   int key_pos = StringFind(block, pattern);
   if(key_pos < 0)
      return("");

   int colon_pos = StringFind(block, ":", key_pos);
   if(colon_pos < 0)
      return("");

   int first_quote = StringFind(block, "\"", colon_pos + 1);
   if(first_quote < 0)
      return("");

   int second_quote = StringFind(block, "\"", first_quote + 1);
   if(second_quote < 0)
      return("");

   return(StringSubstr(block, first_quote + 1, second_quote - first_quote - 1));
}

string DecodeJsonText(string value)
{
   string decoded = value;
   StringReplace(decoded, "\\n", "\n");
   StringReplace(decoded, "\\\"", "\"");
   StringReplace(decoded, "\\\\", "\\");
   return(decoded);
}

double ExtractJsonNumber(string block, string key)
{
   string pattern = "\"" + key + "\"";
   int key_pos = StringFind(block, pattern);
   if(key_pos < 0)
      return(0.0);

   int colon_pos = StringFind(block, ":", key_pos);
   if(colon_pos < 0)
      return(0.0);

   int start = colon_pos + 1;
   while(start < StringLen(block) && StringGetCharacter(block, start) == ' ')
      start++;

   int end = start;
   while(end < StringLen(block))
   {
      ushort c = StringGetCharacter(block, end);
      if((c >= '0' && c <= '9') || c == '.' || c == '-')
         end++;
      else
         break;
   }

   if(end <= start)
      return(0.0);

   return(StringToDouble(StringSubstr(block, start, end - start)));
}

datetime ParseTraderIATime(string timestamp)
{
   string cleaned = timestamp;
   StringReplace(cleaned, "T", " ");
   int plus_pos = StringFind(cleaned, "+");
   if(plus_pos > 0)
      cleaned = StringSubstr(cleaned, 0, plus_pos);
   if(StringLen(cleaned) >= 16 && StringFind(cleaned, "/") > 0)
   {
      string date_part = StringSubstr(cleaned, 0, 10);
      string time_part = StringSubstr(cleaned, 11);
      string day = StringSubstr(date_part, 0, 2);
      string month = StringSubstr(date_part, 3, 2);
      string year = StringSubstr(date_part, 6, 4);
      return(StringToTime(year + "." + month + "." + day + " " + time_part));
   }
   if(StringLen(cleaned) >= 19)
   {
      string iso = StringSubstr(cleaned, 0, 19);
      StringReplace(iso, "-", ".");
      return(StringToTime(iso));
   }
   return(0);
}

datetime GetVisibleSignalTime()
{
   datetime current_bar_time = iTime(_Symbol, _Period, 0);
   if(current_bar_time > 0)
      return(current_bar_time);
   return(TimeCurrent());
}

bool IsTimeVisible(datetime candidate)
{
   if(candidate <= 0)
      return(false);

   datetime first_visible_time = iTime(_Symbol, _Period, MathMax(Bars(_Symbol, _Period) - 1, 0));
   datetime last_visible_time = iTime(_Symbol, _Period, 0);

   if(first_visible_time <= 0 || last_visible_time <= 0)
      return(true);

   if(candidate < first_visible_time)
      return(false);
   if(candidate > last_visible_time + PeriodSeconds(_Period))
      return(false);

   return(true);
}
