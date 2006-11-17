<?xml version="1.0" encoding="ISO-8859-1"?>

<xsl:stylesheet version="1.0"
                xmlns:xsl="http://www.w3.org/1999/XSL/Transform">

 <xsl:preserve-space elements="*" />
 <xsl:output method="xml" indent="yes"
	     encoding="ISO-8859-1"
 />

 <!-- Application keepalive parameter set to 300 by default -->
 <xsl:template match="/server/delays">
  <xsl:copy>
    <xsl:apply-templates select="@*|node()"/>
    <xsl:attribute name="autodeal_max">120</xsl:attribute>
  </xsl:copy>
 </xsl:template>

 <!-- copy the rest verbatim -->
 <xsl:template match="@*|node()">
  <xsl:copy>
   <xsl:apply-templates select="@*|node()"/>
  </xsl:copy>
 </xsl:template>

</xsl:stylesheet>
