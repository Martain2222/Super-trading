//+------------------------------------------------------------------+
//|                                       TestOrderFlowAnalyzer.mq5  |
//|                         EA_SCALPER_XAUUSD - Singularity Edition  |
//|                                                                  |
//| Script de teste para validar o Order Flow Analyzer V2            |
//| Executa diagnósticos e verifica qualidade dos dados              |
//|                                                                  |
//| Test script to validate OrderFlowAnalyzer V2                     |
//| Runs diagnostics and checks tick/data quality                    |
//+------------------------------------------------------------------+
#property copyright "EA_SCALPER_XAUUSD"
#property version   "1.01"
#property script_show_inputs

//--- include principal do analisador
#include <EA_SCALPER\Analysis\OrderFlowAnalyzer_v2.mqh>

//--- parâmetros de entrada
input int              InpBarsToTest   = 10;          // Barras para testar / Bars to test
input ENUM_TIMEFRAMES  InpTimeframe    = PERIOD_M15;  // Timeframe para análise
input int              InpTicksQuality = 1000;        // Nº de ticks para teste de qualidade
input int              InpTicksRT      = 100;         // Nº de ticks para teste em tempo real

//--- forward declarations (organização)
void TestDataQuality(COrderFlowAnalyzerV2 &analyzer);
void TestHistoricalBars(COrderFlowAnalyzerV2 &analyzer,int bars);
void TestRealTimeTicks(COrderFlowAnalyzerV2 &analyzer);
void PrintSummary(COrderFlowAnalyzerV2 &analyzer);

//+------------------------------------------------------------------+
//| Script program start function                                    |
//| Função principal de entrada do script                            |
//+------------------------------------------------------------------+
void OnStart()
{
   Print("========================================================");
   Print("   ORDER FLOW ANALYZER V2 - TESTE DE VALIDACAO");
   Print("   ORDER FLOW ANALYZER V2 - VALIDATION TEST");
   Print("========================================================");
   Print("");

   //--- instancia local do analisador
   COrderFlowAnalyzerV2 analyzer;

   // 1. Inicialização ------------------------------------------------
   Print("1. INICIALIZANDO / INITIALIZING...");
   // 200 barras de histórico, 3.0 desvio mínimo de delta, 0.70 VA ratio
   if(!analyzer.Initialize(_Symbol,InpTimeframe,200,3.0,0.70,METHOD_AUTO))
   {
      Print("ERRO: Falha ao inicializar o analisador!");
      Print("ERROR: Failed to initialize analyzer!");
      return;
   }
   Print("   OK - Inicializado com sucesso / Successfully initialized");
   Print("");

   // 2. Teste de qualidade dos dados --------------------------------
   Print("2. TESTANDO QUALIDADE DOS DADOS / TESTING DATA QUALITY...");
   TestDataQuality(analyzer);
   Print("");

   // 3. Teste de barras históricas ----------------------------------
   Print("3. TESTANDO BARRAS HISTORICAS / TESTING HISTORICAL BARS...");
   TestHistoricalBars(analyzer,InpBarsToTest);
   Print("");

   // 4. Teste de ticks em tempo real --------------------------------
   Print("4. TESTANDO TICKS EM TEMPO REAL / TESTING REAL-TIME TICKS...");
   TestRealTimeTicks(analyzer);
   Print("");

   // 5. Diagnóstico completo ----------------------------------------
   Print("5. DIAGNOSTICO COMPLETO / FULL DIAGNOSTICS...");
   analyzer.PrintDiagnostics();
   Print("");

   // 6. Resumo final -------------------------------------------------
   PrintSummary(analyzer);

   //--- limpeza
   analyzer.Deinitialize();
}
//+------------------------------------------------------------------+
//| Testa qualidade dos dados de tick                                |
//| Checks tick-data flags, volume & last price quality              |
//+------------------------------------------------------------------+
void TestDataQuality(COrderFlowAnalyzerV2 &analyzer)
{
   MqlTick ticks[];
   int copied = CopyTicks(_Symbol,ticks,COPY_TICKS_ALL,0,InpTicksQuality);

   if(copied <= 0)
   {
      Print("   ERRO: Nao foi possivel copiar ticks!");
      Print("   ERROR: Could not copy ticks!");
      return;
   }

   int withBuyFlag   = 0;
   int withSellFlag  = 0;
   int withBothFlags = 0;
   int withNoFlags   = 0;
   int withVolume    = 0;
   int withLast      = 0;

   for(int i=0;i<copied;i++)
   {
      bool hasBuy  = (ticks[i].flags & TICK_FLAG_BUY)  != 0;
      bool hasSell = (ticks[i].flags & TICK_FLAG_SELL) != 0;

      if(hasBuy && hasSell)      withBothFlags++;
      else if(hasBuy)            withBuyFlag++;
      else if(hasSell)           withSellFlag++;
      else                       withNoFlags++;

      if(ticks[i].volume > 0)    withVolume++;
      if(ticks[i].last   > 0)    withLast++;
   }

   Print("   Ticks analisados: ",copied);
   Print("   Com TICK_FLAG_BUY: ", withBuyFlag,
         " (",DoubleToString((double)withBuyFlag/copied*100.0,1),"%)");
   Print("   Com TICK_FLAG_SELL: ",withSellFlag,
         " (",DoubleToString((double)withSellFlag/copied*100.0,1),"%)");
   Print("   Com AMBOS flags: ",   withBothFlags,
         " (",DoubleToString((double)withBothFlags/copied*100.0,1),"%) - INCONSISTENTES!");
   Print("   Sem flags: ",         withNoFlags,
         " (",DoubleToString((double)withNoFlags/copied*100.0,1),"%)");
   Print("   Com volume: ",        withVolume,
         " (",DoubleToString((double)withVolume/copied*100.0,1),"%)");
   Print("   Com last price: ",    withLast,
         " (",DoubleToString((double)withLast/copied*100.0,1),"%)");

   double flagPercent = (double)(withBuyFlag + withSellFlag) / copied * 100.0;

   if(flagPercent >= 80.0)
      Print("   RESULTADO: EXCELENTE - Flags disponiveis!");
   else if(flagPercent >= 50.0)
      Print("   RESULTADO: MODERADO - Flags parcialmente disponiveis");
   else if(flagPercent > 0.0)
      Print("   RESULTADO: FRACO - Poucos flags disponiveis");
   else
      Print("   RESULTADO: SEM FLAGS - Usando metodo alternativo (comparacao de preco)");
}
//+------------------------------------------------------------------+
//| Testa barras historicas                                          |
//| Loops through N historical bars and prints per-bar diagnostics   |
//+------------------------------------------------------------------+
void TestHistoricalBars(COrderFlowAnalyzerV2 &analyzer,int bars)
{
   if(bars <= 0)
   {
      Print("   AVISO: Numero de barras <= 0, nada para testar.");
      Print("   WARNING: Bars to test <= 0, skipping.");
      return;
   }

   int maxBars = MathMin(bars,Bars(_Symbol,InpTimeframe));
   Print("   Processando ",maxBars," barras...");

   for(int i=0;i<maxBars;i++)
   {
      if(!analyzer.ProcessBarTicks(i))
      {
         Print("   Barra ",i,": ERRO ao processar");
         continue;
      }

      SOrderFlowResultV2 result = analyzer.GetResult();
      SValueArea        va     = result.valueArea;

      datetime barTime = iTime(_Symbol,InpTimeframe,i);

      Print(StringFormat(
         "   Barra %d [%s]: Delta=%+d | POC=%.2f | VA=%.2f-%.2f | Ticks=%d | Qual=%s",
         i,
         TimeToString(barTime,TIME_DATE|TIME_MINUTES),
         result.barDelta,
         va.poc,
         va.valow,
         va.vahigh,
         result.totalTicks,
         EnumToString(result.dataQuality)
      ));
   }
}
//+------------------------------------------------------------------+
//| Testa ticks em tempo real                                        |
//| Re-simulates last N ticks and checks signals / divergences       |
//+------------------------------------------------------------------+
void TestRealTimeTicks(COrderFlowAnalyzerV2 &analyzer)
{
   Print("   Processando ",InpTicksRT," ticks recentes...");

   MqlTick ticks[];
   int copied = CopyTicks(_Symbol,ticks,COPY_TICKS_ALL,0,InpTicksRT);

   if(copied <= 0)
   {
      Print("   ERRO: Nao foi possivel copiar ticks!");
      Print("   ERROR: Could not copy ticks!");
      return;
   }

   //--- reseta estado interno para processar do zero
   analyzer.ProcessBarTicks(0);

   //--- processa cada tick do mais antigo para o mais novo
   for(int i=copied-1;i>=0;i--)
      analyzer.ProcessTickDirect(ticks[i]);

   SOrderFlowResultV2 result = analyzer.GetResult();

   Print("   Ticks processados: ", result.totalTicks);
   Print("   Delta: ",           result.barDelta);
   Print("   Buy Volume: ",      result.totalBuyVolume);
   Print("   Sell Volume: ",     result.totalSellVolume);
   Print("   Delta %: ",         DoubleToString(result.deltaPercent,1),"%");
   Print("   Qualidade: ",       EnumToString(result.dataQuality));

   //--- teste de sinais
   int signal = analyzer.GetSignal(100);
   Print("   Sinal: ",
         signal==1  ? "BUY"   :
         signal==-1 ? "SELL"  : "NEUTRO");

   Print("   Divergencia: ",
         analyzer.IsDeltaDivergence() ? "SIM" : "NAO");
   Print("   Absorcao: ",
         analyzer.IsAbsorption(500) ? "SIM" : "NAO");
}
//+------------------------------------------------------------------+
//| Imprime resumo final                                             |
//| Prints final summary & recommendations                           |
//+------------------------------------------------------------------+
void PrintSummary(COrderFlowAnalyzerV2 &analyzer)
{
   Print("========================================================");
   Print("                    RESUMO FINAL");
   Print("========================================================");

   ENUM_DATA_QUALITY quality  = analyzer.GetDataQuality();
   bool              reliable = analyzer.IsDataReliable();

   Print("");
   Print("Simbolo: ",   _Symbol);
   Print("Timeframe: ", EnumToString(InpTimeframe));
   Print("Qualidade dos dados: ", EnumToString(quality));
   Print("Dados confiaveis: ",     reliable ? "SIM" : "NAO");
   Print("");

   if(reliable)
   {
      Print("CONCLUSAO: Order Flow Analyzer esta PRONTO para uso!");
      Print("           Os dados de tick tem qualidade suficiente.");
   }
   else
   {
      Print("ATENCAO: Qualidade dos dados e LIMITADA!");
      Print("         O analyzer usara metodo alternativo (comparacao de preco).");
      Print("         Resultados serao aproximados, nao exatos.");
      Print("");
      Print("RECOMENDACOES:");
      Print("  1. Use com cautela em decisoes de trading");
      Print("  2. Combine com outros indicadores para confirmacao");
      Print("  3. Considere usar broker com melhor feed de dados");
   }

   Print("");
   Print("========================================================");
}
//+------------------------------------------------------------------+
