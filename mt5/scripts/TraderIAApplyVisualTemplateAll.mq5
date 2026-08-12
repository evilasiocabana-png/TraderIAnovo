//+------------------------------------------------------------------+
//| TraderIAApplyVisualTemplateAll                                   |
//| Aplica o template visual a todos os graficos abertos.             |
//+------------------------------------------------------------------+
#property script_show_inputs
#property strict

input string TemplateName = "TraderIAVisualSignals.tpl";

void OnStart()
{
   long chart_id = ChartFirst();
   int applied = 0;
   while(chart_id >= 0)
   {
      if(ChartApplyTemplate(chart_id, TemplateName))
         applied++;
      chart_id = ChartNext(chart_id);
   }
   Print("TraderIA visual template applied to ", applied, " chart(s): ", TemplateName);
}
