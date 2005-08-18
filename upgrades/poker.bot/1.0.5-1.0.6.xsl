<?xml version="1.0" encoding="ISO-8859-1"?>

<xsl:stylesheet version="1.0"
                xmlns:xsl="http://www.w3.org/1999/XSL/Transform">

 <xsl:preserve-space elements="*" />
 <xsl:output method="xml" indent="yes"
	     encoding="ISO-8859-1"
 />

 <xsl:template match="/settings/@poker_network_version">
   <xsl:attribute name="poker_network_version">1.0.6</xsl:attribute>
 </xsl:template>

 <!-- copy the rest verbatim -->
 <xsl:template match="@*|node()">
  <xsl:copy>
   <xsl:apply-templates select="@*|node()"/>
  </xsl:copy>
 </xsl:template>

</xsl:stylesheet>
