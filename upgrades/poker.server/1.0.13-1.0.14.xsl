<?xml version="1.0" encoding="ISO-8859-1"?>

<xsl:stylesheet version="1.0"
                xmlns:xsl="http://www.w3.org/1999/XSL/Transform">

 <xsl:preserve-space elements="*" />
 <xsl:output method="xml" indent="yes"
	     encoding="ISO-8859-1"
 />

 <xsl:template name="timeoutToPlayerTimeout" match="/server/table/@timeout">
   <xsl:attribute name="player_timeout"><xsl:value-of select="/server/table/@timeout"/></xsl:attribute>
 </xsl:template>

 <xsl:template name="addMuckTimeout">
   <xsl:attribute name="muck_timeout">5</xsl:attribute>   
 </xsl:template>

 <xsl:template name="getOrCreateSkin">
   <xsl:if test="not(@skin)">
     <xsl:attribute name="skin">level00</xsl:attribute>
   </xsl:if>
 </xsl:template>
 
 <xsl:template match="/server/table">
  <xsl:copy>
    <xsl:apply-templates select="@*|node()"/>
    <xsl:call-template name="timeoutToPlayerTimeout" />
    <xsl:call-template name="addMuckTimeout" />
    <xsl:call-template name="getOrCreateSkin" />
  </xsl:copy>  
 </xsl:template>

 <!-- copy the rest verbatim -->
 <xsl:template match="@*|node()">
  <xsl:copy>
   <xsl:apply-templates select="@*|node()"/>
  </xsl:copy>  
 </xsl:template>

</xsl:stylesheet>
