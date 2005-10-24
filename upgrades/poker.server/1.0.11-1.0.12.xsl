<?xml version="1.0" encoding="ISO-8859-1"?>

<xsl:stylesheet version="1.0"
                xmlns:xsl="http://www.w3.org/1999/XSL/Transform">

 <xsl:preserve-space elements="*" />
 <xsl:output method="xml" indent="yes"
	     encoding="ISO-8859-1"
 />

 <!-- Application keepalive parameter set to 20 by default -->
 <xsl:template match="/server/@verbose">
   <xsl:attribute name="ping">20</xsl:attribute>
   <xsl:attribute name="verbose"><xsl:value-of select="." /></xsl:attribute>
 </xsl:template>
 
 <!-- Game start negotiations allows to triple the delays -->
 <xsl:template match="/server/delays/@autodeal|/server/delays/@round|/server/delays/@showdown|/server/delays/@finish">
   <xsl:attribute name="{name()}"><xsl:value-of select=". * 3" /></xsl:attribute>
 </xsl:template>

 <!-- Game start negotiations allows to set the position delay to match the timeout delay -->
 <xsl:template match="/server/delays/@position">
   <xsl:attribute name="position">60</xsl:attribute>
 </xsl:template>

 <!-- copy the rest verbatim -->
 <xsl:template match="@*|node()">
  <xsl:copy>
   <xsl:apply-templates select="@*|node()"/>
  </xsl:copy>
 </xsl:template>

</xsl:stylesheet>
