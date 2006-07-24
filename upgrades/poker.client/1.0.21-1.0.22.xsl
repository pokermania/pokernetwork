<?xml version="1.0" encoding="ISO-8859-1"?>

<xsl:stylesheet version="1.0"
                xmlns:xsl="http://www.w3.org/1999/XSL/Transform">

 <xsl:preserve-space elements="*" />
 <xsl:output method="xml" indent="yes"
	     encoding="ISO-8859-1"
 />

 <!-- custom_money is now handled with currency_serial -->
 <xsl:template match="/settings/lobby/@custom_money">
   <xsl:variable name="custom_money_value" select="." />
   <xsl:attribute name="currency_serial">
     <xsl:if test="$custom_money_value='y'">2</xsl:if>
     <xsl:if test="$custom_money_value='n'">1</xsl:if>
   </xsl:attribute>
 </xsl:template>

 <xsl:template match="/settings/tournaments/@custom_money">
   <xsl:variable name="custom_money_value" select="." />
   <xsl:attribute name="currency_serial">
     <xsl:if test="$custom_money_value='y'">2</xsl:if>
     <xsl:if test="$custom_money_value='n'">1</xsl:if>
   </xsl:attribute>
 </xsl:template>

 <!-- copy the rest verbatim -->
 <xsl:template match="@*|node()">
  <xsl:copy>
   <xsl:apply-templates select="@*|node()"/>
  </xsl:copy>
 </xsl:template>

</xsl:stylesheet>
